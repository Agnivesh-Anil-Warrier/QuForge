"""Resumable training engine with epoch checkpointing, early stopping, and metric tracking."""

import json
import os
import random
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
import yaml

from qforge.data import load_cached_dataset
from qforge.evaluate import compute_metrics
from qforge.models import HybridQCQModel
from qforge.utils import configure_cpu_threads, set_seed


class Trainer:
    """Resumable training engine for QForge hybrid models."""

    def __init__(
        self,
        config: Dict[str, Any],
        run_dir: Union[str, Path],
        device: Optional[torch.device] = None,
    ):
        self.config = config
        self.run_dir = Path(run_dir)
        self.run_dir.mkdir(parents=True, exist_ok=True)

        # 1. Hardware & System Setup
        self.device = device or torch.device(config.get("system", {}).get("device", "cpu"))
        num_threads = config.get("system", {}).get("torch_threads")
        self.num_threads = configure_cpu_threads(num_threads)

        self.seed = config.get("system", {}).get("seed", 42)
        set_seed(self.seed)

        # 2. Dataset Caching & Loaders
        cache_dir = config.get("dataset", {}).get("cache_dir", "data/cache")
        self.train_dataset = load_cached_dataset(cache_dir, "train")
        self.val_dataset = load_cached_dataset(cache_dir, "val")
        self.test_dataset = load_cached_dataset(cache_dir, "test")

        batch_size = config.get("training", {}).get("batch_size", 32)
        num_workers = config.get("training", {}).get("num_workers", 0)

        self.train_loader = DataLoader(
            self.train_dataset,
            batch_size=batch_size,
            shuffle=True,
            num_workers=num_workers,
            pin_memory=False,
        )
        self.val_loader = DataLoader(
            self.val_dataset,
            batch_size=batch_size,
            shuffle=False,
            num_workers=num_workers,
            pin_memory=False,
        )
        self.test_loader = DataLoader(
            self.test_dataset,
            batch_size=batch_size,
            shuffle=False,
            num_workers=num_workers,
            pin_memory=False,
        )

        # 3. Model Construction
        model_cfg = config.get("model", {})
        self.filter_mode = model_cfg.get("filter_mode", "frozen_random")
        self.filter_depth = model_cfg.get("filter_depth", 1)

        self.model = HybridQCQModel(
            filter_mode=self.filter_mode,
            filter_depth=self.filter_depth,
            seed=self.seed,
            cache_dir=cache_dir,
        ).to(self.device)

        # 4. Optimizer & Loss Function
        train_cfg = config.get("training", {})
        lr_backbone = float(train_cfg.get("lr_backbone", 1e-3))
        lr_filter = float(train_cfg.get("lr_quantum_filter", 1e-2))
        weight_decay = float(train_cfg.get("weight_decay", 1e-4))

        param_groups = self.model.get_parameter_groups(
            lr_backbone=lr_backbone,
            lr_filter=lr_filter,
        )
        self.optimizer = torch.optim.Adam(param_groups, weight_decay=weight_decay)

        # Class weighted loss handling
        pos_weight_val = train_cfg.get("pos_weight", None)
        if pos_weight_val is not None:
            pos_weight_t = torch.tensor([float(pos_weight_val)], device=self.device)
            self.criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight_t)
        else:
            self.criterion = nn.BCEWithLogitsLoss()

        # 5. Training State & Checkpoint Paths
        self.max_epochs = train_cfg.get("max_epochs", 100)
        self.patience = train_cfg.get("early_stopping_patience", 15)

        self.latest_ckpt_path = self.run_dir / "checkpoint_latest.pt"
        self.best_ckpt_path = self.run_dir / "checkpoint_best.pt"
        self.history_csv_path = self.run_dir / "history.csv"
        self.metrics_json_path = self.run_dir / "metrics.json"
        self.config_yaml_path = self.run_dir / "config.yaml"

        self.start_epoch = 1
        self.best_val_acc = -1.0
        self.patience_counter = 0
        self.is_finished = False
        self.history: List[Dict[str, Any]] = []

    def save_checkpoint(self, epoch: int, is_best: bool = False) -> None:
        """Save training state for seamless resumption."""
        state = {
            "epoch": epoch,
            "model_state_dict": self.model.state_dict(),
            "optimizer_state_dict": self.optimizer.state_dict(),
            "best_val_acc": self.best_val_acc,
            "patience_counter": self.patience_counter,
            "is_finished": self.is_finished,
            "history": self.history,
            "rng_state": {
                "torch": torch.get_rng_state(),
                "numpy": np.random.get_state(),
                "python": random.getstate(),
            },
        }
        torch.save(state, self.latest_ckpt_path)
        if is_best:
            torch.save(state, self.best_ckpt_path)

    def load_checkpoint_if_exists(self) -> bool:
        """Resume state from latest checkpoint if available.
        
        Returns:
            True if a valid checkpoint was resumed, False otherwise.
        """
        if not self.latest_ckpt_path.exists():
            return False

        print(f"Resuming from checkpoint: {self.latest_ckpt_path}")
        state = torch.load(self.latest_ckpt_path, map_location=self.device, weights_only=False)

        self.model.load_state_dict(state["model_state_dict"])
        self.optimizer.load_state_dict(state["optimizer_state_dict"])
        self.start_epoch = state["epoch"] + 1
        self.best_val_acc = state["best_val_acc"]
        self.patience_counter = state.get("patience_counter", 0)
        self.is_finished = state.get("is_finished", False)
        if self.start_epoch <= self.max_epochs:
            self.is_finished = False
        self.history = state.get("history", [])

        # Restore RNG states
        if "rng_state" in state:
            rng = state["rng_state"]
            torch.set_rng_state(rng["torch"])
            np.random.set_state(rng["numpy"])
            random.setstate(rng["python"])

        print(f"Resumed at epoch {self.start_epoch} (Best Val Acc: {self.best_val_acc:.4f})")
        return True

    def train_epoch(self) -> Tuple[float, float, float]:
        """Run one epoch of training.
        
        Returns:
            Tuple of (train_loss, train_acc, filter_grad_norm)
        """
        self.model.train()
        total_loss = 0.0
        all_preds = []
        all_targets = []
        last_filter_grad_norm = 0.0

        for X_batch, y_batch in self.train_loader:
            X_batch = X_batch.to(self.device)
            y_batch = y_batch.to(self.device)

            self.optimizer.zero_grad()
            logits = self.model(X_batch)
            loss = self.criterion(logits, y_batch)
            loss.backward()

            # Record quantum filter gradient norm if in trainable mode
            if self.filter_mode == "trainable" and self.model.quantum_filter.weights.grad is not None:
                last_filter_grad_norm = float(self.model.quantum_filter.weights.grad.norm().item())

            self.optimizer.step()

            total_loss += float(loss.item()) * len(y_batch)
            probs = torch.sigmoid(logits).detach().cpu().numpy()
            all_preds.extend(probs)
            all_targets.extend(y_batch.detach().cpu().numpy())

        avg_loss = total_loss / len(self.train_dataset)
        preds_bin = (np.array(all_preds) >= 0.5).astype(int)
        acc = float((preds_bin == np.array(all_targets)).mean())
        return avg_loss, acc, last_filter_grad_norm

    @torch.no_grad()
    def evaluate_split(self, loader: DataLoader) -> Dict[str, Any]:
        """Evaluate model on a DataLoader split."""
        self.model.eval()
        total_loss = 0.0
        all_probs = []
        all_targets = []

        for X_batch, y_batch in loader:
            X_batch = X_batch.to(self.device)
            y_batch = y_batch.to(self.device)

            logits = self.model(X_batch)
            loss = self.criterion(logits, y_batch)
            total_loss += float(loss.item()) * len(y_batch)

            probs = torch.sigmoid(logits).cpu().numpy()
            all_probs.extend(probs)
            all_targets.extend(y_batch.cpu().numpy())

        avg_loss = total_loss / len(loader.dataset)
        metrics = compute_metrics(np.array(all_targets), np.array(all_probs))
        metrics["loss"] = float(avg_loss)
        return metrics

    def run(self) -> Dict[str, Any]:
        """Execute full training and final evaluation workflow."""
        # 1. Save config copy
        with open(self.config_yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(self.config, f, default_flow_style=False)

        # 2. Check if already completed
        if self.metrics_json_path.exists():
            print(f"Run already finished in {self.run_dir}. Loading metrics.json.")
            with open(self.metrics_json_path, "r", encoding="utf-8") as f:
                return json.load(f)

        # 3. Check for existing checkpoint
        self.load_checkpoint_if_exists()

        if not self.is_finished:
            print(f"Starting training: {self.filter_mode} mode, {self.max_epochs} max epochs, patience={self.patience}")
            print(f"{'Epoch':<6} | {'Train Loss':<10} | {'Train Acc':<9} | {'Val Loss':<8} | {'Val Acc':<8} | {'Drift':<7} | {'Time':<6}")
            print("-" * 65)

            for epoch in range(self.start_epoch, self.max_epochs + 1):
                t0 = time.perf_counter()
                train_loss, train_acc, grad_norm = self.train_epoch()
                val_metrics = self.evaluate_split(self.val_loader)
                val_loss = val_metrics["loss"]
                val_acc = val_metrics["accuracy"]
                duration = time.perf_counter() - t0

                drift = self.model.quantum_filter.parameter_drift

                is_best = False
                if val_acc > self.best_val_acc:
                    self.best_val_acc = val_acc
                    self.patience_counter = 0
                    is_best = True
                else:
                    self.patience_counter += 1

                epoch_record = {
                    "epoch": epoch,
                    "train_loss": round(train_loss, 4),
                    "train_acc": round(train_acc, 4),
                    "val_loss": round(val_loss, 4),
                    "val_acc": round(val_acc, 4),
                    "val_f1": round(val_metrics["f1"], 4),
                    "val_auc": round(val_metrics["roc_auc"], 4),
                    "parameter_drift": round(drift, 6),
                    "filter_grad_norm": round(grad_norm, 6),
                    "epoch_duration_sec": round(duration, 2),
                }
                self.history.append(epoch_record)

                print(
                    f"{epoch:<6} | {train_loss:<10.4f} | {train_acc:<9.4f} | "
                    f"{val_loss:<8.4f} | {val_acc:<8.4f} | {drift:<7.4f} | {duration:<5.1f}s"
                    f"{' *' if is_best else ''}"
                )

                # Save history.csv and checkpoint every epoch
                pd.DataFrame(self.history).to_csv(self.history_csv_path, index=False)
                self.save_checkpoint(epoch, is_best=is_best)

                # Early stopping check
                if self.patience_counter >= self.patience:
                    print(f"Early stopping triggered at epoch {epoch} (Patience: {self.patience}).")
                    break

            self.is_finished = True
            self.save_checkpoint(epoch, is_best=False)

        # 4. Final Evaluation on Test Set using Best Checkpoint
        print("\nLoading best validation checkpoint for final test evaluation...")
        if self.best_ckpt_path.exists():
            best_state = torch.load(self.best_ckpt_path, map_location=self.device, weights_only=False)
            self.model.load_state_dict(best_state["model_state_dict"])
            print(f"Best checkpoint loaded from epoch {best_state['epoch']} (Val Acc: {best_state['best_val_acc']:.4f})")
        else:
            print("Warning: best checkpoint not found, evaluating with current model weights.")

        test_metrics = self.evaluate_split(self.test_loader)
        print("\nFinal Test Metrics:")
        for k, v in test_metrics.items():
            print(f"  {k}: {v}")

        final_results = {
            "experiment": self.config.get("experiment_name", "qforge_exp"),
            "filter_mode": self.filter_mode,
            "filter_depth": self.filter_depth,
            "seed": self.seed,
            "best_val_acc": self.best_val_acc,
            "test_metrics": test_metrics,
            "final_parameter_drift": self.model.quantum_filter.parameter_drift,
            "total_epochs_trained": len(self.history),
        }

        with open(self.metrics_json_path, "w", encoding="utf-8") as f:
            json.dump(final_results, f, indent=2)

        return final_results
