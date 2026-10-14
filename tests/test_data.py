"""Tests for Phase 1 data pipeline: manifests, splits disjointness, and cached tensors."""

from pathlib import Path
import numpy as np
import pandas as pd
import pytest
import torch

from qforge.data import load_cached_dataset, load_dataset_manifest


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SPLITS_DIR = PROJECT_ROOT / "data" / "splits"
CACHE_DIR = PROJECT_ROOT / "data" / "cache"


def test_manifests_exist_and_non_empty():
    for split in ["train", "val", "test"]:
        csv_path = SPLITS_DIR / f"{split}.csv"
        assert csv_path.exists(), f"Missing split manifest: {csv_path}"
        df = pd.read_csv(csv_path)
        assert len(df) > 0, f"Manifest {split}.csv is empty"
        assert "label" in df.columns
        assert "md5" in df.columns
        assert "phash" in df.columns
        assert set(df["label"].unique()).issubset({0, 1})


def test_splits_are_disjoint():
    train_df = pd.read_csv(SPLITS_DIR / "train.csv")
    val_df = pd.read_csv(SPLITS_DIR / "val.csv")
    test_df = pd.read_csv(SPLITS_DIR / "test.csv")

    train_files = set(train_df["file_name"])
    val_files = set(val_df["file_name"])
    test_files = set(test_df["file_name"])

    # Disjointness checks
    assert len(train_files.intersection(val_files)) == 0, "Train and Val share files!"
    
    # Check MD5 hash disjointness
    train_md5 = set(train_df["md5"])
    val_md5 = set(val_df["md5"])
    test_md5 = set(test_df["md5"])

    assert len(train_md5.intersection(val_md5)) == 0, "Train and Val share exact MD5 hashes!"
    assert len(train_md5.intersection(test_md5)) == 0, "Train and Test share exact MD5 hashes (leakage)!"
    assert len(val_md5.intersection(test_md5)) == 0, "Val and Test share exact MD5 hashes (leakage)!"


def test_cached_tensors_integrity():
    for split in ["train", "val", "test"]:
        df = pd.read_csv(SPLITS_DIR / f"{split}.csv")
        dataset = load_cached_dataset(CACHE_DIR, split)
        
        assert len(dataset) == len(df), f"Dataset length mismatch for {split}"
        
        x_sample, y_sample = dataset[0]
        assert isinstance(x_sample, torch.Tensor)
        assert isinstance(y_sample, torch.Tensor)
        assert x_sample.shape == (1, 28, 28), f"Unexpected tensor shape {x_sample.shape}"
        assert 0.0 <= x_sample.min() <= 1.0
        assert 0.0 <= x_sample.max() <= 1.0
        assert y_sample.item() in [0.0, 1.0]
