"""Dataset loading, binary label mapping, split manifests, and deduplication logic."""

from pathlib import Path
from typing import Dict, List, Tuple, Any
import numpy as np
import pandas as pd
import torch


def load_dataset_manifest(splits_dir: str | Path, split: str) -> pd.DataFrame:
    """Load train/val/test CSV manifest."""
    manifest_path = Path(splits_dir) / f"{split}.csv"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")
    return pd.read_csv(manifest_path)
