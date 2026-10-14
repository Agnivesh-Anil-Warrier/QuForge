"""CLI entrypoint to execute a single experiment configuration."""

import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Run QForge experiment")
    parser.add_argument("--config", type=str, default="configs/base.yaml", help="Path to config YAML")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--mode", type=str, default="frozen_random", choices=["frozen_random", "trainable", "classical_conv", "none"])
    args = parser.parse_args()
    print(f"Running QForge with config: {args.config}, mode: {args.mode}, seed: {args.seed}")


if __name__ == "__main__":
    main()
