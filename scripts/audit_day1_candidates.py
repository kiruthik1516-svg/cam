"""Audit Utility for Stage 1 Candidate Crops (Day 1)

Usage:
    python scripts/audit_day1_candidates.py
"""

from __future__ import annotations
from pathlib import Path
from collections import defaultdict
import datetime
import json

CANDIDATES_DIR = Path(r"D:\facial\data\stage1_candidates\day_01")

def audit_candidates():
    if not CANDIDATES_DIR.exists():
        print(f"Directory {CANDIDATES_DIR} does not exist.")
        return

    files = sorted(list(CANDIDATES_DIR.glob("*.jpg")))
    print("=" * 80)
    print("STAGE 1 CANDIDATES AUDIT: DAY 1")
    print(f"Path: {CANDIDATES_DIR}")
    print(f"Total Extracted Candidate Frames: {len(files):,}")
    print("=" * 80)

    clips = defaultdict(list)
    for f in files:
        parts = f.name.split("_w")
        if len(parts) >= 2:
            stem = parts[0].replace("day01_", "")
            clips[stem].append(f)

    print(f"{'#':<4} {'Clip Timestamp':<20} {'Clip Hash':<16} {'Frames':<10} {'Windows':<10}")
    print("-" * 80)

    total_frames = 0
    for idx, (stem, flist) in enumerate(sorted(clips.items()), 1):
        ts_raw = stem.split("_")[-1]
        formatted_ts = f"{ts_raw[:4]}-{ts_raw[4:6]}-{ts_raw[6:8]} {ts_raw[8:10]}:{ts_raw[10:12]}:{ts_raw[12:14]}"
        hash_prefix = stem.split("_")[4][:12]
        
        # Count unique windows
        win_set = set(f.name.split("_w")[1].split("_")[0] for f in flist)
        print(f"{idx:<4} {formatted_ts:<20} {hash_prefix:<16} {len(flist):<10} {len(win_set):<10}")
        total_frames += len(flist)

    print("-" * 80)
    print(f"Total Active Clips Extracted: {len(clips)}")
    print(f"Total Candidates:             {total_frames:,} frames")
    print("=" * 80)

if __name__ == "__main__":
    audit_candidates()

