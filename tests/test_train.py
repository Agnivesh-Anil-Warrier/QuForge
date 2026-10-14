"""Unit tests for Phase 3 training engine: parameter groups, checkpoint resumption, and metrics tracking."""

import json
from pathlib import Path
import shutil
import numpy as np
import pytest
import torch

from qforge.models import HybridQCQModel
from qforge.train import Trainer
from qforge.utils import load_config


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_optimizer_parameter_groups():
    """Verify separate parameter groups with distinct learning rates for backbone vs quantum filter."""
    model_tr = HybridQCQModel(filter_mode="trainable", seed=42)
    groups = model_tr.get_parameter_groups(lr_backbone=1e-3, lr_filter=1e-2)

    assert len(groups) == 2, "Expected 2 parameter groups in trainable mode!"
    assert groups[0]["name"] == "quantum_filter"
    assert groups[0]["lr"] == 1e-2
    assert groups[1]["name"] == "backbone_and_head"
    assert groups[1]["lr"] == 1e-3

    # Frozen mode should have only 1 group
    model_fr = HybridQCQModel(filter_mode="frozen_random", seed=42)
    groups_fr = model_fr.get_parameter_groups(lr_backbone=1e-3, lr_filter=1e-2)
    assert len(groups_fr) == 1, "Expected 1 parameter group in frozen mode!"
    assert groups_fr[0]["name"] == "backbone_and_head"


def test_training_and_resumption_workflow(tmp_path):
    """Test full training loop for 2 epochs, interrupt, resume for 2 more epochs, and verify state continuity."""
    config_path = PROJECT_ROOT / "configs" / "base.yaml"
    config = load_config(config_path)

    # Fast configuration for unit test
    config["training"]["max_epochs"] = 2
    config["training"]["early_stopping_patience"] = 10
    config["model"]["filter_mode"] = "trainable"
    config["experiment_name"] = "test_resume_exp"

    test_run_dir = tmp_path / "test_run"

    # Part 1: Train 2 epochs
    trainer = Trainer(config, run_dir=test_run_dir)
    # Monkey-patch loaders to run on tiny subset for speed
    tiny_train = torch.utils.data.Subset(trainer.train_dataset, range(64))
    tiny_val = torch.utils.data.Subset(trainer.val_dataset, range(32))
    tiny_test = torch.utils.data.Subset(trainer.test_dataset, range(32))
    trainer.train_loader = torch.utils.data.DataLoader(tiny_train, batch_size=32)
    trainer.val_loader = torch.utils.data.DataLoader(tiny_val, batch_size=32)
    trainer.test_loader = torch.utils.data.DataLoader(tiny_test, batch_size=32)

    trainer.run()

    assert (test_run_dir / "checkpoint_latest.pt").exists()
    assert (test_run_dir / "checkpoint_best.pt").exists()
    assert (test_run_dir / "history.csv").exists()
    assert (test_run_dir / "metrics.json").exists()

    with open(test_run_dir / "metrics.json", "r") as f:
        metrics1 = json.load(f)
    assert metrics1["total_epochs_trained"] == 2
    assert "accuracy" in metrics1["test_metrics"]
    assert "roc_auc" in metrics1["test_metrics"]

    # Part 2: Resume training to 4 epochs
    # Remove metrics.json so runner continues
    (test_run_dir / "metrics.json").unlink()
    config["training"]["max_epochs"] = 4

    trainer2 = Trainer(config, run_dir=test_run_dir)
    trainer2.train_loader = torch.utils.data.DataLoader(tiny_train, batch_size=32)
    trainer2.val_loader = torch.utils.data.DataLoader(tiny_val, batch_size=32)
    trainer2.test_loader = torch.utils.data.DataLoader(tiny_test, batch_size=32)

    resumed = trainer2.load_checkpoint_if_exists()
    assert resumed is True
    assert trainer2.start_epoch == 3

    trainer2.run()

    with open(test_run_dir / "metrics.json", "r") as f:
        metrics2 = json.load(f)
    assert metrics2["total_epochs_trained"] == 4
    assert len(trainer2.history) == 4


def test_deterministic_reproducibility(tmp_path):
    """Verify that identical seeds produce bitwise-identical model weights and loss trajectory."""
    config_path = PROJECT_ROOT / "configs" / "base.yaml"
    config = load_config(config_path)

    config["training"]["max_epochs"] = 2
    config["model"]["filter_mode"] = "trainable"
    config["system"]["seed"] = 777

    losses1 = []
    losses2 = []

    # Run 1
    dir1 = tmp_path / "run1"
    trainer1 = Trainer(config, run_dir=dir1)
    tiny_train = torch.utils.data.Subset(trainer1.train_dataset, range(32))
    tiny_val = torch.utils.data.Subset(trainer1.val_dataset, range(32))
    tiny_test = torch.utils.data.Subset(trainer1.test_dataset, range(32))
    trainer1.train_loader = torch.utils.data.DataLoader(tiny_train, batch_size=16)
    trainer1.val_loader = torch.utils.data.DataLoader(tiny_val, batch_size=16)
    trainer1.test_loader = torch.utils.data.DataLoader(tiny_test, batch_size=16)
    trainer1.run()
    losses1 = [h["train_loss"] for h in trainer1.history]

    # Run 2 (same seed)
    dir2 = tmp_path / "run2"
    trainer2 = Trainer(config, run_dir=dir2)
    trainer2.train_loader = torch.utils.data.DataLoader(tiny_train, batch_size=16)
    trainer2.val_loader = torch.utils.data.DataLoader(tiny_val, batch_size=16)
    trainer2.test_loader = torch.utils.data.DataLoader(tiny_test, batch_size=16)
    trainer2.run()
    losses2 = [h["train_loss"] for h in trainer2.history]

    assert losses1 == losses2, f"Loss trajectories differ: {losses1} vs {losses2}"
    for p1, p2 in zip(trainer1.model.parameters(), trainer2.model.parameters()):
        assert torch.allclose(p1, p2, atol=1e-6), "Model parameters differ across identical seed runs!"

