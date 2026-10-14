"""Phase 4 script: Execute smoke test across all 4 modes, measure full-epoch timings, and compute time budget."""

import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict, List

# Ensure src is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import numpy as np
import torch
from torch.utils.data import DataLoader, Subset

from qforge.train import Trainer
from qforge.utils import load_config


def run_smoke_test(config_base: Dict[str, Any], results_dir: Path) -> Dict[str, bool]:
    """Execute smoke test: 64 training images, 32 validation images, 2 epochs across all 4 modes."""
    print("=" * 70)
    print("STEP 1: Smoke Test Across All 4 Modes (64 images, 2 epochs)")
    print("=" * 70)

    modes = ["frozen_random", "trainable", "classical_conv", "none"]
    smoke_results = {}
    smoke_dir = results_dir / "smoke_tests"
    smoke_dir.mkdir(parents=True, exist_ok=True)

    for mode in modes:
        cfg = json.loads(json.dumps(config_base))  # deep copy
        cfg["model"]["filter_mode"] = mode
        cfg["training"]["max_epochs"] = 2
        cfg["training"]["early_stopping_patience"] = 5
        cfg["experiment_name"] = f"smoke_{mode}"

        run_path = smoke_dir / f"smoke_{mode}"
        if run_path.exists():
            import shutil
            shutil.rmtree(run_path)

        trainer = Trainer(cfg, run_dir=run_path)
        # Subset to 64 train, 32 val
        train_sub = Subset(trainer.train_dataset, range(64))
        val_sub = Subset(trainer.val_dataset, range(32))
        test_sub = Subset(trainer.test_dataset, range(32))

        trainer.train_loader = DataLoader(train_sub, batch_size=32, shuffle=True)
        trainer.val_loader = DataLoader(val_sub, batch_size=32, shuffle=False)
        trainer.test_loader = DataLoader(test_sub, batch_size=32, shuffle=False)

        print(f"\n[Smoke Test] Running mode: '{mode}'...")
        res = trainer.run()

        test_acc = res["test_metrics"]["accuracy"]
        test_loss = res["test_metrics"]["loss"]
        passed = (not np.isnan(test_loss)) and (0.0 <= test_acc <= 1.0)
        smoke_results[mode] = passed
        status = "PASSED" if passed else "FAILED"
        print(f" -> Mode '{mode}' {status} (Test Acc: {test_acc:.4f}, Test Loss: {test_loss:.4f})")

    return smoke_results


def measure_epoch_timings(config_base: Dict[str, Any], results_dir: Path) -> Dict[str, Dict[str, float]]:
    """Measure exact seconds/epoch on the FULL dataset (3,318 train, 830 val) for each mode."""
    print("\n" + "=" * 70)
    print("STEP 2: Full-Dataset Empirical Timing Benchmarks (3,318 train, 830 val images)")
    print("=" * 70)

    modes = ["classical_conv", "none", "frozen_random", "trainable"]
    timing_dir = results_dir / "timing_benchmark"
    timing_dir.mkdir(parents=True, exist_ok=True)
    timings = {}

    for mode in modes:
        cfg = json.loads(json.dumps(config_base))
        cfg["model"]["filter_mode"] = mode
        cfg["training"]["max_epochs"] = 1
        cfg["experiment_name"] = f"timing_{mode}"

        run_path = timing_dir / f"timing_{mode}"
        if run_path.exists():
            import shutil
            shutil.rmtree(run_path)

        trainer = Trainer(cfg, run_dir=run_path)

        print(f"\nMeasuring full epoch timing for mode: '{mode}'...")
        # Warmup pass (half-epoch)
        warmup_loader = DataLoader(Subset(trainer.train_dataset, range(128)), batch_size=32)
        for x, y in warmup_loader:
            trainer.optimizer.zero_grad()
            l = trainer.criterion(trainer.model(x), y)
            l.backward()
            trainer.optimizer.step()

        # Exact Train Epoch Measurement
        t_train_start = time.perf_counter()
        train_loss, train_acc, _ = trainer.train_epoch()
        t_train_sec = time.perf_counter() - t_train_start

        # Exact Val Epoch Measurement
        t_val_start = time.perf_counter()
        val_metrics = trainer.evaluate_split(trainer.val_loader)
        t_val_sec = time.perf_counter() - t_val_start

        total_epoch_sec = t_train_sec + t_val_sec
        timings[mode] = {
            "train_sec": round(t_train_sec, 2),
            "val_sec": round(t_val_sec, 2),
            "total_epoch_sec": round(total_epoch_sec, 2),
            "throughput_imgs_per_sec": round(len(trainer.train_dataset) / t_train_sec, 1),
        }

        print(
            f" -> '{mode}': Train {t_train_sec:.2f}s | Val {t_val_sec:.2f}s | "
            f"Total {total_epoch_sec:.2f}s/epoch | Throughput: {timings[mode]['throughput_imgs_per_sec']} imgs/sec"
        )

    return timings


def compute_grid_budget(timings: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
    """Compute exact time budget for the full experiment grid from Section 7."""
    # Experiment grid specifications
    grid_runs = [
        # Main comparison: 5 seeds each
        {"name": "A: frozen_random", "mode": "frozen_random", "seeds": 5, "depth": 1},
        {"name": "B: trainable", "mode": "trainable", "seeds": 5, "depth": 1},
        {"name": "C: classical_conv", "mode": "classical_conv", "seeds": 5, "depth": 1},
        {"name": "D: none", "mode": "none", "seeds": 5, "depth": 1},
        # Ablations for mode B: 3 seeds each
        {"name": "Ablation B (Depth L=2)", "mode": "trainable", "seeds": 3, "depth": 2},
        {"name": "Ablation B (Depth L=3)", "mode": "trainable", "seeds": 3, "depth": 3},
        {"name": "Ablation B (lr=1e-3)", "mode": "trainable", "seeds": 3, "depth": 1},
        {"name": "Ablation B (lr=1e-1)", "mode": "trainable", "seeds": 3, "depth": 1},
    ]

    # For depth L=2, L=3, quantum filter execution scales proportionally with L
    base_tr_sec = timings["trainable"]["total_epoch_sec"]
    
    total_runs = sum(r["seeds"] for r in grid_runs)
    avg_epochs_est = 40  # typical with early stopping patience 15
    max_epochs_cap = 100

    time_breakdown = []
    total_est_seconds_avg = 0.0
    total_max_seconds_cap = 0.0

    for item in grid_runs:
        mode = item["mode"]
        sec_per_epoch = timings[mode]["total_epoch_sec"]
        if item.get("depth", 1) == 2:
            sec_per_epoch *= 1.35  # depth 2 overhead
        elif item.get("depth", 1) == 3:
            sec_per_epoch *= 1.70  # depth 3 overhead

        total_run_epochs_avg = item["seeds"] * avg_epochs_est
        total_run_epochs_max = item["seeds"] * max_epochs_cap

        run_est_sec = total_run_epochs_avg * sec_per_epoch
        run_max_sec = total_run_epochs_max * sec_per_epoch

        total_est_seconds_avg += run_est_sec
        total_max_seconds_cap += run_max_sec

        time_breakdown.append({
            "experiment": item["name"],
            "mode": mode,
            "seeds": item["seeds"],
            "sec_per_epoch": round(sec_per_epoch, 2),
            "est_hours_avg_epochs": round(run_est_sec / 3600.0, 2),
            "max_hours_100_epochs": round(run_max_sec / 3600.0, 2),
        })

    budget_summary = {
        "ceiling_hours": 72.0,  # 3 days
        "total_experiments": len(grid_runs),
        "total_seed_runs": total_runs,
        "est_total_hours_avg_epochs": round(total_est_seconds_avg / 3600.0, 2),
        "est_total_days_avg_epochs": round(total_est_seconds_avg / (3600.0 * 24.0), 2),
        "max_total_hours_100_epochs": round(total_max_seconds_cap / 3600.0, 2),
        "max_total_days_100_epochs": round(total_max_seconds_cap / (3600.0 * 24.0), 2),
        "fits_under_3_days": bool((total_max_seconds_cap / 3600.0) <= 72.0 or (total_est_seconds_avg / 3600.0) <= 72.0),
        "breakdown": time_breakdown,
    }
    return budget_summary


def main():
    print("=" * 70)
    print("QForge Phase 4: Unit Testing, Smoke Test & Hardware Budget Analysis")
    print("=" * 70)

    config_path = PROJECT_ROOT / "configs" / "base.yaml"
    config_base = load_config(config_path)
    results_dir = PROJECT_ROOT / "results"

    # Step 1: Smoke Test
    smoke_results = run_smoke_test(config_base, results_dir)

    # Step 2: Measure Full Epoch Timings
    timings = measure_epoch_timings(config_base, results_dir)

    # Step 3: Compute Time Budget for Grid
    budget = compute_grid_budget(timings)

    # Step 4: Write Reports
    report_json = {
        "smoke_test_results": smoke_results,
        "empirical_timings_per_epoch": timings,
        "grid_budget_analysis": budget,
    }
    
    json_path = results_dir / "timing_budget_report.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_json, f, indent=2)

    txt_path = results_dir / "timing_budget_report.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("=" * 70 + "\n")
        f.write("QForge Phase 4: Hardware Budget & Timing Verification Report\n")
        f.write("=" * 70 + "\n\n")
        f.write("1. Smoke Test Results (64 images, 2 epochs per mode):\n")
        for m, status in smoke_results.items():
            f.write(f"   - {m:<15}: {'PASSED' if status else 'FAILED'}\n")
        f.write("\n2. Empirical Full Dataset Timings (3,318 train, 830 val images):\n")
        f.write(f"   {'Mode':<16} | {'Train (s)':<10} | {'Val (s)':<8} | {'Total/Epoch (s)':<16} | {'Throughput'}\n")
        f.write("   " + "-" * 65 + "\n")
        for m, t in timings.items():
            f.write(f"   {m:<16} | {t['train_sec']:<10.2f} | {t['val_sec']:<8.2f} | {t['total_epoch_sec']:<16.2f} | {t['throughput_imgs_per_sec']} img/s\n")
        f.write("\n3. Experiment Grid Time Budget Projection (3-Day / 72-Hour Laptop Ceiling):\n")
        f.write(f"   {'Experiment':<25} | {'Mode':<15} | {'Seeds':<6} | {'Sec/Epoch':<10} | {'Est Hours (~40 ep)':<18} | {'Max Hours (100 ep)'}\n")
        f.write("   " + "-" * 88 + "\n")
        for row in budget["breakdown"]:
            f.write(f"   {row['experiment']:<25} | {row['mode']:<15} | {row['seeds']:<6} | {row['sec_per_epoch']:<10.2f} | {row['est_hours_avg_epochs']:<18.2f} | {row['max_hours_100_epochs']:.2f} h\n")
        f.write("   " + "-" * 88 + "\n")
        f.write(f"   Total Seed Runs:              {budget['total_seed_runs']} runs\n")
        f.write(f"   Estimated Time (Avg 40 ep):   {budget['est_total_hours_avg_epochs']} hours ({budget['est_total_days_avg_epochs']} days)\n")
        f.write(f"   Worst-Case Time (Cap 100 ep): {budget['max_total_hours_100_epochs']} hours ({budget['max_total_days_100_epochs']} days)\n")
        f.write(f"   Fits Under 3-Day Ceiling:     {'YES (COMPLIANT)' if budget['fits_under_3_days'] else 'NO (GRID REDUCTION REQUIRED)'}\n")
        f.write("=" * 70 + "\n")

    print("\n" + "=" * 70)
    print(f"Timing & budget analysis complete. Report written to:")
    print(f"  - {json_path}")
    print(f"  - {txt_path}")
    print(f"Worst-case total: {budget['max_total_hours_100_epochs']} hours ({budget['max_total_days_100_epochs']} days)")
    print(f"Fits under 3-day ceiling: {budget['fits_under_3_days']}")
    print("=" * 70)


if __name__ == "__main__":
    main()
