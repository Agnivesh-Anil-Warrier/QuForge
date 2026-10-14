"""Dataset loading, binary label mapping, stratified splitting, deduplication, and caching."""

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import imagehash
import numpy as np
import pandas as pd
from PIL import Image
from sklearn.model_selection import train_test_split
import torch
from torch.utils.data import Dataset


def load_dataset_manifest(splits_dir: Union[str, Path], split: str) -> pd.DataFrame:
    """Load train/val/test CSV manifest."""
    manifest_path = Path(splits_dir) / f"{split}.csv"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")
    return pd.read_csv(manifest_path)


def compute_hashes(img_path: Union[str, Path]) -> Tuple[str, str]:
    """Compute MD5 hash and perceptual hash (phash) of an image.
    
    Args:
        img_path: Path to the image file.
        
    Returns:
        Tuple of (md5_hex_string, phash_hex_string)
    """
    path = Path(img_path)
    with open(path, "rb") as f:
        file_bytes = f.read()
    md5 = hashlib.md5(file_bytes).hexdigest()

    with Image.open(path) as img:
        img_rgb = img.convert("RGB")
        phash_val = str(imagehash.phash(img_rgb))

    return md5, phash_val


def scan_dataset(
    raw_dir: Union[str, Path],
    label_mapping: Dict[str, Optional[int]],
) -> pd.DataFrame:
    """Scan raw directory (containing Training/ and Testing/ folders) and build manifest.
    
    Excludes any class mapped to None in label_mapping (e.g. 'notumor').
    """
    raw_path = Path(raw_dir)
    if not raw_path.exists():
        raise FileNotFoundError(f"Raw dataset directory does not exist: {raw_path}")

    records = []
    
    for split_dir_name in ["Training", "Testing"]:
        split_dir = raw_path / split_dir_name
        if not split_dir.exists():
            continue

        for class_dir in sorted(split_dir.iterdir()):
            if not class_dir.is_dir():
                continue
            class_name = class_dir.name.lower()
            label = label_mapping.get(class_name, None)
            
            # Exclude class if label is None
            if label is None:
                continue

            for img_file in sorted(class_dir.iterdir()):
                if img_file.suffix.lower() in [".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"]:
                    records.append({
                        "raw_split": "train" if split_dir_name == "Training" else "test",
                        "folder": split_dir_name,
                        "class_name": class_name,
                        "label": int(label),
                        "file_name": img_file.name,
                        "full_path": str(img_file.resolve()),
                        "rel_path": str(img_file.relative_to(raw_path)),
                    })

    df = pd.DataFrame(records)
    return df


def audit_and_deduplicate(
    df: pd.DataFrame,
    phash_threshold: int = 0,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Audit images for MD5 duplicates and perceptual hash collisions, removing leakage.
    
    Rules for leakage elimination:
    1. If an image in Testing collides with an image in Training, the Testing image is dropped.
    2. Exact duplicate images within Training are deduplicated (keeping the first).
    3. Exact duplicate images within Testing are deduplicated.
    
    Args:
        df: Scanned manifest DataFrame.
        phash_threshold: Hamming distance threshold for perceptual hash collision (0 = exact match).
        
    Returns:
        Tuple of (clean_df, deduplication_report_dict)
    """
    print(f"Auditing {len(df)} images for exact and near duplicates...")
    
    md5_list = []
    phash_list = []
    for idx, row in df.iterrows():
        md5, ph = compute_hashes(row["full_path"])
        md5_list.append(md5)
        phash_list.append(ph)

    df = df.copy()
    df["md5"] = md5_list
    df["phash"] = phash_list

    report: Dict[str, Any] = {
        "initial_total_images": len(df),
        "initial_train_images": int((df["raw_split"] == "train").sum()),
        "initial_test_images": int((df["raw_split"] == "test").sum()),
        "exact_md5_duplicates": 0,
        "leakage_test_dropped_md5": 0,
        "leakage_test_dropped_phash": 0,
        "internal_train_dropped": 0,
        "internal_test_dropped": 0,
        "dropped_indices": [],
        "dropped_details": [],
    }

    # Step 1: Detect exact MD5 duplicates
    train_mask = df["raw_split"] == "train"
    test_mask = df["raw_split"] == "test"

    train_md5s = set(df.loc[train_mask, "md5"])
    
    # Check test-to-train leakage via MD5
    leakage_test_md5_idx = df[test_mask & df["md5"].isin(train_md5s)].index.tolist()
    for idx in leakage_test_md5_idx:
        report["dropped_details"].append({
            "idx": idx,
            "path": df.loc[idx, "rel_path"],
            "reason": "Test-to-Train leakage (exact MD5 collision)",
            "md5": df.loc[idx, "md5"],
        })
    report["leakage_test_dropped_md5"] = len(leakage_test_md5_idx)

    # Step 2: Internal duplicates within Training (exact MD5)
    train_df = df[train_mask]
    train_dup_mask = train_df.duplicated(subset=["md5"], keep="first")
    internal_train_dup_idx = train_df[train_dup_mask].index.tolist()
    for idx in internal_train_dup_idx:
        report["dropped_details"].append({
            "idx": idx,
            "path": df.loc[idx, "rel_path"],
            "reason": "Internal Training duplicate (exact MD5 collision)",
            "md5": df.loc[idx, "md5"],
        })
    report["internal_train_dropped"] = len(internal_train_dup_idx)

    # Step 3: Internal duplicates within Testing (exact MD5)
    test_remaining = df[test_mask & ~df.index.isin(leakage_test_md5_idx)]
    test_dup_mask = test_remaining.duplicated(subset=["md5"], keep="first")
    internal_test_dup_idx = test_remaining[test_dup_mask].index.tolist()
    for idx in internal_test_dup_idx:
        report["dropped_details"].append({
            "idx": idx,
            "path": df.loc[idx, "rel_path"],
            "reason": "Internal Testing duplicate (exact MD5 collision)",
            "md5": df.loc[idx, "md5"],
        })
    report["internal_test_dropped"] = len(internal_test_dup_idx)

    to_drop = set(leakage_test_md5_idx + internal_train_dup_idx + internal_test_dup_idx)

    # Step 4: Perceptual hash collision audit (Hamming distance <= phash_threshold)
    cleaned_temp = df[~df.index.isin(to_drop)].copy()
    train_phashes = {
        imagehash.hex_to_hash(h): idx 
        for idx, h in zip(cleaned_temp[cleaned_temp["raw_split"] == "train"].index, 
                          cleaned_temp[cleaned_temp["raw_split"] == "train"]["phash"])
    }

    phash_leakage_idx = []
    test_clean_subset = cleaned_temp[cleaned_temp["raw_split"] == "test"]
    for idx, row in test_clean_subset.iterrows():
        thash = imagehash.hex_to_hash(row["phash"])
        for tr_hash, tr_idx in train_phashes.items():
            dist = thash - tr_hash
            if dist <= phash_threshold:
                phash_leakage_idx.append(idx)
                report["dropped_details"].append({
                    "idx": idx,
                    "path": row["rel_path"],
                    "reason": f"Test-to-Train perceptual hash collision (dist={dist})",
                    "matching_train_path": df.loc[tr_idx, "rel_path"],
                    "phash": row["phash"],
                })
                break
                
    report["leakage_test_dropped_phash"] = len(phash_leakage_idx)
    to_drop.update(phash_leakage_idx)

    report["dropped_indices"] = sorted(list(to_drop))
    report["total_dropped"] = len(to_drop)
    
    clean_df = df[~df.index.isin(to_drop)].copy().reset_index(drop=True)
    report["final_total_images"] = len(clean_df)
    report["final_train_images"] = int((clean_df["raw_split"] == "train").sum())
    report["final_test_images"] = int((clean_df["raw_split"] == "test").sum())

    return clean_df, report


def create_splits(
    clean_df: pd.DataFrame,
    val_ratio: float = 0.2,
    seed: int = 42,
) -> Dict[str, pd.DataFrame]:
    """Split training pool into stratified train and validation sets (80/20), keeping test set separate.
    
    Args:
        clean_df: Cleaned dataset manifest.
        val_ratio: Proportion of training pool allocated to validation.
        seed: Random state for deterministic stratified split.
        
    Returns:
        Dict with keys 'train', 'val', 'test' mapping to their respective DataFrames.
    """
    train_pool = clean_df[clean_df["raw_split"] == "train"].copy().reset_index(drop=True)
    test_df = clean_df[clean_df["raw_split"] == "test"].copy().reset_index(drop=True)

    train_idx, val_idx = train_test_split(
        np.arange(len(train_pool)),
        test_size=val_ratio,
        stratify=train_pool["label"],
        random_state=seed,
    )

    train_df = train_pool.iloc[train_idx].copy().reset_index(drop=True)
    val_df = train_pool.iloc[val_idx].copy().reset_index(drop=True)

    train_df["split"] = "train"
    val_df["split"] = "val"
    test_df["split"] = "test"

    return {
        "train": train_df,
        "val": val_df,
        "test": test_df,
    }


def save_split_manifests(
    splits: Dict[str, pd.DataFrame],
    splits_dir: Union[str, Path],
) -> None:
    """Save train.csv, val.csv, and test.csv split manifests."""
    out_dir = Path(splits_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for split_name, df in splits.items():
        csv_path = out_dir / f"{split_name}.csv"
        df.to_csv(csv_path, index=False)
        print(f"Saved manifest: {csv_path} ({len(df)} samples)")


def preprocess_image(img_path: Union[str, Path], target_size: Tuple[int, int] = (28, 28)) -> np.ndarray:
    """Load image, convert to single-channel grayscale, resize, and normalize to [0, 1].
    
    Returns:
        np.ndarray of shape (1, target_size[0], target_size[1]), dtype float32.
    """
    with Image.open(img_path) as img:
        gray = img.convert("L")
        resized = gray.resize(target_size, Image.Resampling.BILINEAR)
        arr = np.array(resized, dtype=np.float32) / 255.0
        arr = np.expand_dims(arr, axis=0)  # Shape (1, H, W)
        return arr


def preprocess_and_cache_tensors(
    splits: Dict[str, pd.DataFrame],
    cache_dir: Union[str, Path],
    image_size: Tuple[int, int] = (28, 28),
) -> Dict[str, Tuple[np.ndarray, np.ndarray]]:
    """Preprocess all images across splits and cache them as .npy files on disk.
    
    Files generated:
        X_train.npy, y_train.npy
        X_val.npy, y_val.npy
        X_test.npy, y_test.npy
        
    Returns:
        Dict of {split: (X_tensor, y_tensor)}
    """
    out_dir = Path(cache_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cached_data = {}

    for split_name, df in splits.items():
        print(f"Preprocessing {split_name} split ({len(df)} images)...")
        num_samples = len(df)
        X = np.zeros((num_samples, 1, image_size[0], image_size[1]), dtype=np.float32)
        y = np.array(df["label"].values, dtype=np.float32)

        for i, (_, row) in enumerate(df.iterrows()):
            X[i] = preprocess_image(row["full_path"], target_size=image_size)

        x_path = out_dir / f"X_{split_name}.npy"
        y_path = out_dir / f"y_{split_name}.npy"
        np.save(x_path, X)
        np.save(y_path, y)
        print(f"Cached {split_name} tensors -> {x_path} {X.shape}, {y_path} {y.shape}")
        cached_data[split_name] = (X, y)

    return cached_data


def compute_dataset_summary(
    splits: Dict[str, pd.DataFrame],
    class_names: Dict[int, str] = {0: "Benign", 1: "Malignant"},
) -> Dict[str, Any]:
    """Compute exact sample counts, class distributions, and recommended loss weighting."""
    summary: Dict[str, Any] = {"splits": {}}

    for split_name, df in splits.items():
        counts = df["label"].value_counts().to_dict()
        n_benign = int(counts.get(0, 0))
        n_malignant = int(counts.get(1, 0))
        total = len(df)
        
        summary["splits"][split_name] = {
            "total": total,
            "benign_0": n_benign,
            "malignant_1": n_malignant,
            "benign_ratio": round(n_benign / total, 4) if total > 0 else 0,
            "malignant_ratio": round(n_malignant / total, 4) if total > 0 else 0,
            "classes_breakdown": df["class_name"].value_counts().to_dict(),
        }

    # Compute loss weighting based on training split
    train_summary = summary["splits"]["train"]
    n_neg = train_summary["benign_0"]
    n_pos = train_summary["malignant_1"]
    
    # pos_weight for BCEWithLogitsLoss (weight for positive class 1)
    pos_weight = round(n_neg / n_pos, 4) if n_pos > 0 else 1.0
    
    summary["loss_weighting"] = {
        "pos_weight": pos_weight,
        "interpretation": f"Positive class (Malignant) weighted {pos_weight:.4f}x relative to Benign",
        "class_counts": {"benign (0)": n_neg, "malignant (1)": n_pos},
    }

    return summary


class CachedMRIDataset(Dataset):
    """In-memory PyTorch Dataset backed by cached numpy arrays."""

    def __init__(self, X: np.ndarray, y: np.ndarray):
        assert len(X) == len(y), f"X and y must have same length: {len(X)} vs {len(y)}"
        self.X = torch.from_numpy(X).float()
        self.y = torch.from_numpy(y).float()

    def __len__(self) -> int:
        return len(self.X)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        return self.X[idx], self.y[idx]


def load_cached_dataset(
    cache_dir: Union[str, Path],
    split: str,
) -> CachedMRIDataset:
    """Load cached dataset split directly from disk into memory."""
    cpath = Path(cache_dir)
    x_file = cpath / f"X_{split}.npy"
    y_file = cpath / f"y_{split}.npy"
    if not x_file.exists() or not y_file.exists():
        raise FileNotFoundError(f"Cached files not found in {cpath} for split {split}")
    X = np.load(x_file)
    y = np.load(y_file)
    return CachedMRIDataset(X, y)
