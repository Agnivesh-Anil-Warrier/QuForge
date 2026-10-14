"""CLI runner for executing single QForge experiments."""

import argparse
from pathlib import Path
import sys

# Ensure src is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import yaml
from qforge.train import Trainer
from qforge.utils import load_config


def parse_args():
    parser = argparse.ArgumentParser(description="Run QForge single experiment")
    parser.add_argument("--config", type=str, default="configs/base.yaml", help="Path to config file")
    parser.add_argument("--mode", type=str, default=None, choices=["frozen_random", "trainable", "classical_conv", "none"], help="Quantum filter mode")
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    parser.add_argument("--depth", type=int, default=None, help="Quantum filter depth L")
    parser.add_argument("--epochs", type=int, default=None, help="Max training epochs")
    parser.add_argument("--lr-filter", type=float, default=None, help="Quantum filter learning rate")
    parser.add_argument("--lr-backbone", type=float, default=None, help="Backbone learning rate")
    parser.add_argument("--patience", type=int, default=None, help="Early stopping patience")
    parser.add_argument("--run-name", type=str, default=None, help="Custom run name")
    return parser.parse_args()


def main():
    args = parse_args()
    config_path = PROJECT_ROOT / args.config
    config = load_config(config_path)

    # CLI Overrides
    if args.mode:
        config["model"]["filter_mode"] = args.mode
    if args.depth:
        config["model"]["filter_depth"] = args.depth
    if args.seed is not None:
        config["system"]["seed"] = args.seed
    if args.epochs:
        config["training"]["max_epochs"] = args.epochs
    if args.lr_filter:
        config["training"]["lr_quantum_filter"] = args.lr_filter
    if args.lr_backbone:
        config["training"]["lr_backbone"] = args.lr_backbone
    if args.patience:
        config["training"]["early_stopping_patience"] = args.patience

    mode = config["model"]["filter_mode"]
    seed = config["system"]["seed"]
    run_name = args.run_name or f"exp_{mode}_seed{seed}"
    config["experiment_name"] = run_name

    run_dir = PROJECT_ROOT / "results" / "runs" / run_name
    print(f"Launching experiment: {run_name}")
    print(f"Filter mode: {mode}, Seed: {seed}, Run directory: {run_dir}")

    trainer = Trainer(config, run_dir=run_dir)
    results = trainer.run()
    print("\nExperiment execution completed successfully.")
    return results


if __name__ == "__main__":
    main()
