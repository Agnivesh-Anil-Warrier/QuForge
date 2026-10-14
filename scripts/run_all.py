"""Phase 5 script: Automated sequential experiment grid runner with progress logging and resume capability."""

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict, List

# Ensure src is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import pandas as pd
import yaml

from qforge.train import Trainer
from qforge.utils import load_config


def build_experiment_queue(seeds_main: List[int], seeds_ablation: List[int]) -> List[Dict[str, Any]]:
    """Build the ordered list of experiments to run.
    
    Priority Order (per guide.md):
      1. Model A (frozen_random) & Model B (trainable) first for early key comparison.
      2. Model C (classical_conv) control baseline.
      3. Model D (none) CNN baseline.
      4. Ablation Depth L in {2, 3} for Model B.
      5. Ablation Learning Rate in {1e-3, 1e-1} for Model B.
    """
    queue = []

    # 1. Main A: frozen_random baseline (Paper baseline)
    for s in seeds_main:
        queue.append({
            "exp_id": f"model_A_frozen_seed{s}",
            "group": "main_A_frozen",
            "mode": "frozen_random",
            "seed": s,
            "depth": 1,
            "lr_filter": 0.01,
        })

    # 2. Main B: trainable quantum filter (Our core contribution)
    for s in seeds_main:
        queue.append({
            "exp_id": f"model_B_trainable_seed{s}",
            "group": "main_B_trainable",
            "mode": "trainable",
            "seed": s,
            "depth": 1,
            "lr_filter": 0.01,
        })

    # 3. Main C: classical_conv control
    for s in seeds_main:
        queue.append({
            "exp_id": f"model_C_classical_seed{s}",
            "group": "main_C_classical",
            "mode": "classical_conv",
            "seed": s,
            "depth": 1,
            "lr_filter": 0.01,
        })

    # 4. Main D: none (direct CNN baseline)
    for s in seeds_main:
        queue.append({
            "exp_id": f"model_D_none_seed{s}",
            "group": "main_D_none",
            "mode": "none",
            "seed": s,
            "depth": 1,
            "lr_filter": 0.01,
        })

    # 5. Ablations for Model B (Depth L=2, L=3)
    for depth in [2, 3]:
        for s in seeds_ablation:
            queue.append({
                "exp_id": f"ablation_depth_L{depth}_seed{s}",
                "group": f"ablation_depth_L{depth}",
                "mode": "trainable",
                "seed": s,
                "depth": depth,
                "lr_filter": 0.01,
            })

    # 6. Ablations for Model B (lr_filter = 1e-3, 1e-1)
    for lr in [0.001, 0.1]:
        lr_tag = "1e-3" if lr == 0.001 else "1e-1"
        for s in seeds_ablation:
            queue.append({
                "exp_id": f"ablation_lr_{lr_tag}_seed{s}",
                "group": f"ablation_lr_{lr_tag}",
                "mode": "trainable",
                "seed": s,
                "depth": 1,
                "lr_filter": lr,
            })

    return queue


def write_progress_log(
    log_file: Path,
    message: str,
    also_print: bool = True,
) -> None:
    """Append message with timestamp to progress log file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {message}"
    if also_print:
        print(formatted)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(formatted + "\n")


def update_interim_summary(runs_dir: Path, summary_csv: Path) -> None:
    """Scan completed runs and build interim summary CSV."""
    records = []
    if not runs_dir.exists():
        return

    for exp_dir in sorted(runs_dir.iterdir()):
        if not exp_dir.is_dir():
            continue
        metrics_file = exp_dir / "metrics.json"
        if not metrics_file.exists():
            continue

        try:
            with open(metrics_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            t_m = data.get("test_metrics", {})
            records.append({
                "experiment": data.get("experiment", exp_dir.name),
                "filter_mode": data.get("filter_mode", ""),
                "filter_depth": data.get("filter_depth", 1),
                "seed": data.get("seed", 42),
                "epochs_trained": data.get("total_epochs_trained", 0),
                "best_val_acc": round(data.get("best_val_acc", 0.0), 4),
                "test_acc": round(t_m.get("accuracy", 0.0), 4),
                "test_bal_acc": round(t_m.get("balanced_accuracy", 0.0), 4),
                "test_f1": round(t_m.get("f1", 0.0), 4),
                "test_auc": round(t_m.get("roc_auc", 0.0), 4),
                "test_loss": round(t_m.get("loss", 0.0), 4),
                "param_drift": round(data.get("final_parameter_drift", 0.0), 6),
            })
        except Exception:
            continue

    if records:
        df = pd.DataFrame(records)
        df.to_csv(summary_csv, index=False)


def main():
    parser = argparse.ArgumentParser(description="QForge sequential grid experiment runner")
    parser.add_argument("--config", type=str, default="configs/base.yaml", help="Base config path")
    parser.add_argument("--seeds-main", nargs="+", type=int, default=[42, 43, 44, 45, 46], help="Seeds for main grid (default 5)")
    parser.add_argument("--seeds-ablation", nargs="+", type=int, default=[42, 43, 44], help="Seeds for ablations (default 3)")
    parser.add_argument("--max-epochs", type=int, default=None, help="Override max epochs")
    parser.add_argument("--patience", type=int, default=None, help="Override early stopping patience")
    parser.add_argument("--limit-runs", type=int, default=None, help="Limit number of runs (for debugging/testing)")
    args = parser.parse_args()

    config_path = PROJECT_ROOT / args.config
    base_config = load_config(config_path)

    results_dir = PROJECT_ROOT / "results"
    runs_dir = results_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    log_file = results_dir / "progress.log"
    summary_csv = results_dir / "interim_summary.csv"

    # Build queue
    queue = build_experiment_queue(args.seeds_main, args.seeds_ablation)
    if args.limit_runs:
        queue = queue[: args.limit_runs]

    total_runs = len(queue)
    start_time_all = time.perf_counter()

    write_progress_log(log_file, "=" * 75)
    write_progress_log(log_file, f"QForge Phase 5: Commencing Experiment Grid Execution ({total_runs} total runs)")
    write_progress_log(log_file, f"Main Seeds: {args.seeds_main} | Ablation Seeds: {args.seeds_ablation}")
    write_progress_log(log_file, "=" * 75)

    completed_durations = []

    for i, item in enumerate(queue, 1):
        exp_id = item["exp_id"]
        run_dir = runs_dir / exp_id
        metrics_path = run_dir / "metrics.json"

        # Check if already completed
        if metrics_path.exists():
            write_progress_log(log_file, f"[{i}/{total_runs}] SKIPPING (Already completed): {exp_id}")
            update_interim_summary(runs_dir, summary_csv)
            continue

        write_progress_log(
            log_file,
            f"[{i}/{total_runs}] STARTING: {exp_id} | Mode: {item['mode']} | "
            f"Seed: {item['seed']} | Depth: {item['depth']} | lr_filter: {item['lr_filter']}"
        )

        # Clone config & override
        cfg = json.loads(json.dumps(base_config))
        cfg["experiment_name"] = exp_id
        cfg["model"]["filter_mode"] = item["mode"]
        cfg["model"]["filter_depth"] = item["depth"]
        cfg["training"]["lr_quantum_filter"] = item["lr_filter"]
        cfg["system"]["seed"] = item["seed"]
        if args.max_epochs:
            cfg["training"]["max_epochs"] = args.max_epochs
        if args.patience:
            cfg["training"]["early_stopping_patience"] = args.patience

        run_start = time.perf_counter()
        trainer = Trainer(cfg, run_dir=run_dir)
        results = trainer.run()
        run_duration = time.perf_counter() - run_start
        completed_durations.append(run_duration)

        # Telemetry
        test_acc = results["test_metrics"]["accuracy"]
        val_acc = results["best_val_acc"]
        f1 = results["test_metrics"]["f1"]
        auc = results["test_metrics"]["roc_auc"]
        drift = results.get("final_parameter_drift", 0.0)
        epochs = results.get("total_epochs_trained", 0)

        # Time estimation
        avg_run_dur = sum(completed_durations) / len(completed_durations)
        runs_left = total_runs - i
        est_sec_left = runs_left * avg_run_dur
        est_hours_left = est_sec_left / 3600.0

        write_progress_log(
            log_file,
            f"[{i}/{total_runs}] COMPLETED: {exp_id} in {run_duration:.1f}s ({epochs} epochs) | "
            f"Val Acc: {val_acc:.4f} | Test Acc: {test_acc:.4f} | F1: {f1:.4f} | "
            f"AUC: {auc:.4f} | Drift: {drift:.6f} | Est. Time Left: {est_hours_left:.2f}h"
        )
        write_progress_log(log_file, "-" * 75)

        # Update interim summary
        update_interim_summary(runs_dir, summary_csv)

    total_elapsed_all = time.perf_counter() - start_time_all
    write_progress_log(log_file, "=" * 75)
    write_progress_log(
        log_file,
        f"EXPERIMENT GRID COMPLETE! Finished {total_runs} runs in "
        f"{total_elapsed_all / 3600.0:.2f} hours ({total_elapsed_all / 60.0:.1f} mins)."
    )
    write_progress_log(log_file, f"Final summary saved to: {summary_csv}")
    write_progress_log(log_file, "=" * 75)


if __name__ == "__main__":
    main()
