"""Utility helpers for seeding, logging, configuration loading, and timing."""

import os
import random
import time
from pathlib import Path
from typing import Any, Dict
import numpy as np
import torch
import yaml


def set_seed(seed: int = 42) -> None:
    """Set random seed across Python, NumPy, and PyTorch for deterministic execution."""
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(False)  # True can break some CPU ops; set False for stability


def load_config(config_path: str | Path) -> Dict[str, Any]:
    """Load configuration from a YAML file."""
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def configure_cpu_threads(num_threads: int | None = None) -> int:
    """Configure PyTorch CPU thread count to avoid thread contention.
    
    Defaults to (physical_cores - 1), or minimum 1.
    """
    if num_threads is None:
        import os
        total_cores = os.cpu_count() or 4
        # Allocate approximately physical cores (half of logical if hyperthreaded) or total - 1
        num_threads = max(1, (total_cores // 2) if total_cores > 4 else total_cores - 1)
    torch.set_num_threads(num_threads)
    return num_threads


class Timer:
    """Context manager for measuring elapsed execution time."""

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.end = time.perf_counter()
        self.elapsed = self.end - self.start
