"""Phase 1 execution script: Scan, deduplicate, split, preprocess, and cache Kaggle MRI dataset."""

import json
import os
import sys
import time
from pathlib import Path

# Add project root and src to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import yaml
from qforge.data import (
    scan_dataset,
    audit_and_deduplicate,
    create_splits,
    save_split_manifests,
    preprocess_and_cache_tensors,
    compute_dataset_summary,
)


def main():
    print("=" * 70)
    print("QForge Phase 1: Data Pipeline, Deduplication & Preprocessing")
    print("=" * 70)

    config_path = PROJECT_ROOT / "configs" / "base.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    dataset_cfg = config["dataset"]
    raw_dir = PROJECT_ROOT / dataset_cfg["raw_dir"]
    splits_dir = PROJECT_ROOT / dataset_cfg["splits_dir"]
    cache_dir = PROJECT_ROOT / dataset_cfg["cache_dir"]
    results_dir = PROJECT_ROOT / "results"
    
    label_mapping = dataset_cfg["label_mapping"]
    image_size = tuple(dataset_cfg["image_size"])
    val_ratio = dataset_cfg["train_val_ratio"][1]
    seed = dataset_cfg["split_seed"]

    print(f"Dataset raw directory: {raw_dir}")
    print(f"Splits directory:      {splits_dir}")
    print(f"Cache directory:       {cache_dir}")
    print(f"Target image size:     {image_size}")
    print(f"Label mapping:         {label_mapping}")
    print(f"Validation ratio:      {val_ratio} (Seed: {seed})")

    # Step 1: Scan raw dataset
    print("\n--- [Step 1/5] Scanning Raw Dataset ---")
    start_time = time.perf_counter()
    df_raw = scan_dataset(raw_dir, label_mapping)
    print(f"Found {len(df_raw)} valid tumor images (notumor images excluded).")
    print(df_raw.groupby(["raw_split", "class_name", "label"]).size())

    # Step 2: Audit and deduplicate
    print("\n--- [Step 2/5] Hash-based Deduplication & Leakage Elimination ---")
    clean_df, dedup_report = audit_and_deduplicate(df_raw, phash_threshold=0)
    print(f"Deduplication complete.")
    print(f" - Initial total:               {dedup_report['initial_total_images']}")
    print(f" - Test-to-Train MD5 leakage:   {dedup_report['leakage_test_dropped_md5']} dropped from test")
    print(f" - Test-to-Train pHash leakage: {dedup_report['leakage_test_dropped_phash']} dropped from test")
    print(f" - Internal Train duplicates:   {dedup_report['internal_train_dropped']} dropped from train")
    print(f" - Internal Test duplicates:    {dedup_report['internal_test_dropped']} dropped from test")
    print(f" - Total dropped images:        {dedup_report['total_dropped']}")
    print(f" - Final clean images:          {dedup_report['final_total_images']}")

    # Save deduplication report
    dedup_path = results_dir / "deduplication_report.json"
    with open(dedup_path, "w", encoding="utf-8") as f:
        json.dump(dedup_report, f, indent=2)
    print(f"Saved deduplication report to {dedup_path}")

    # Step 3: Stratified splitting
    print("\n--- [Step 3/5] Stratified 80/20 Train/Validation Split ---")
    splits = create_splits(clean_df, val_ratio=val_ratio, seed=seed)
    save_split_manifests(splits, splits_dir)

    # Step 4: Preprocessing and tensor caching
    print("\n--- [Step 4/5] Grayscale Preprocessing, Resizing & Tensor Caching ---")
    cached_tensors = preprocess_and_cache_tensors(splits, cache_dir, image_size=image_size)

    # Step 5: Summary metrics and loss weighting
    print("\n--- [Step 5/5] Data Summary & Class Weight Calculation ---")
    summary = compute_dataset_summary(splits)
    
    # Save summary json
    summary_json_path = results_dir / "data_summary.json"
    with open(summary_json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    # Format human-readable summary text
    summary_txt_path = results_dir / "data_summary.txt"
    with open(summary_txt_path, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("QForge Dataset Summary Report (Kaggle Brain Tumor MRI)\n")
        f.write("=" * 60 + "\n\n")
        f.write("Binary Classification Mapping:\n")
        f.write("  - Malignant (1): Glioma\n")
        f.write("  - Benign (0):    Meningioma + Pituitary\n")
        f.write("  - Excluded:      Notumor (dropped per study protocol)\n\n")
        f.write("-" * 60 + "\n")
        f.write(f"{'Split':<10} | {'Total':<8} | {'Benign (0)':<12} | {'Malignant (1)':<14} | {'Malignant Ratio'}\n")
        f.write("-" * 60 + "\n")
        for s_name in ["train", "val", "test"]:
            s_data = summary["splits"][s_name]
            f.write(f"{s_name:<10} | {s_data['total']:<8} | {s_data['benign_0']:<12} | {s_data['malignant_1']:<14} | {s_data['malignant_ratio'] * 100:.2f}%\n")
        f.write("-" * 60 + "\n\n")
        f.write("Class Breakdown Details:\n")
        for s_name in ["train", "val", "test"]:
            f.write(f"  {s_name.upper()} Breakdown: {summary['splits'][s_name]['classes_breakdown']}\n")
        f.write("\nClass Imbalance & Loss Weighting:\n")
        f.write(f"  Training Benign (0):     {summary['loss_weighting']['class_counts']['benign (0)']}\n")
        f.write(f"  Training Malignant (1):  {summary['loss_weighting']['class_counts']['malignant (1)']}\n")
        f.write(f"  BCE pos_weight:          {summary['loss_weighting']['pos_weight']}\n")
        f.write(f"  Interpretation:          {summary['loss_weighting']['interpretation']}\n")
        f.write("\nPreprocessing & Cache:\n")
        f.write(f"  Image Dimension:         {image_size} (1 channel grayscale)\n")
        f.write("  Value Scaling:           [0.0, 1.0] float32\n")
        f.write(f"  Cache Files:             X_train.npy, y_train.npy, X_val.npy, y_val.npy, X_test.npy, y_test.npy in {cache_dir}\n")
        f.write("=" * 60 + "\n")

    print(f"\nSaved data summary to {summary_json_path} and {summary_txt_path}")
    elapsed = time.perf_counter() - start_time
    print(f"\nPhase 1 Pipeline successfully executed in {elapsed:.2f} seconds!")
    print("=" * 70)


if __name__ == "__main__":
    main()
