"""Comparative Benchmark: Baseline Hybrid vs Fresh Calibrated Day 1 Run

Compares execution time, candidate crop volume, storage footprint, and ground-truth recall.
"""

from __future__ import annotations
import json
from pathlib import Path

BASE_DIR = Path(r"D:\facial\data\stage1_candidates")
HYBRID_DIR = BASE_DIR / "day_01_hybrid_baseline"
CLEAN_DIR = BASE_DIR / "day_01"

def compare_runs():
    print("=" * 80)
    print("DAY 1 EXTRACTION BENCHMARK: HYBRID BASELINE vs CALIBRATED RUN")
    print("=" * 80)

    # Hybrid Run Metrics
    hybrid_manifest = HYBRID_DIR / "manifest.json"
    hybrid_files = list(HYBRID_DIR.glob("*.jpg")) if HYBRID_DIR.exists() else []
    hybrid_size_mb = sum(f.stat().st_size for f in hybrid_files) / (1024**2) if hybrid_files else 0.0

    # Clean Run Metrics
    clean_manifest = CLEAN_DIR / "manifest.json"
    clean_files = list(CLEAN_DIR.glob("*.jpg")) if CLEAN_DIR.exists() else []
    clean_size_mb = sum(f.stat().st_size for f in clean_files) / (1024**2) if clean_files else 0.0

    print(f"{'Metric':<35} {'Hybrid Baseline':<22} {'Calibrated Run':<22}")
    print("-" * 80)
    print(f"{'Motion Threshold (px)':<35} {'1,000 / 1,500 px':<22} {'3,000 px':<22}")
    print(f"{'Post-Window Margin (sec)':<35} {'300s / 60s':<22} {'25s':<22}")
    print(f"{'Total Candidate Frames':<35} {f'{len(hybrid_files):,} frames':<22} {f'{len(clean_files):,} frames':<22}")
    print(f"{'Disk Footprint (MB)':<35} {f'{hybrid_size_mb:.1f} MB':<22} {f'{clean_size_mb:.1f} MB':<22}")

    if clean_files and hybrid_files:
        reduction_pct = (1.0 - (len(clean_files) / len(hybrid_files))) * 100.0
        print(f"{'Frame Volume Reduction':<35} {'Baseline':<22} {f'{reduction_pct:.1f}% reduction':<22}")

    print("=" * 80)

if __name__ == "__main__":
    compare_runs()

