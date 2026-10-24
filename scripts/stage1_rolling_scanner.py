"""Industrial CCTV Fast Rolling Candidate Scanner (Stage 1)

Solves physical disk and compute bottlenecks:
1. Sequentially copies video from external USB HDD (E:) to local NVMe SSD (D:) at 137 MB/s (zero head thrashing).
2. Uses Intel Iris Xe hardware decode (-hwaccel d3d11va) and C-level scene motion filtering.
3. Performs 1:1 lossless pixel crop to perimeter mask [295, 20, 1490, 780] (preserves native face resolution without downscaling).
4. Auto-prunes local staging buffer after each clip, maintaining <2 GB SSD usage.
5. Emits day-by-day candidate images and manifest.json.
"""

from __future__ import annotations

import argparse
import datetime
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("RollingScanner")

# Calibrated observation perimeter mask [x1, y1, x2, y2]
# Crop parameters: width = 1195, height = 760, x = 295, y = 20
CROP_W = 1195
CROP_H = 760
CROP_X = 295
CROP_Y = 20
SCENE_THRESH = 0.015


def process_clip(
    src_clip: Path,
    staging_dir: Path,
    output_dir: Path,
    day_num: int,
    clip_index: int,
    total_clips: int
) -> dict:
    fname = src_clip.name
    clip_stem = src_clip.stem
    staged_clip = staging_dir / fname

    logger.info(f"[{clip_index}/{total_clips}] Staging {fname[:32]}... from USB HDD...")
    t0 = time.time()
    
    # 1. Sequential copy from USB HDD to local NVMe SSD
    try:
        shutil.copyfile(src_clip, staged_clip)
    except Exception as e:
        logger.error(f"Failed to copy {fname}: {e}")
        return {"file": fname, "status": "copy_error", "candidates": 0, "duration": 0}
        
    t_copy = time.time() - t0
    sz_mb = staged_clip.stat().st_size / (1024 * 1024)
    logger.info(f"  Staged {sz_mb:.1f} MB in {t_copy:.2f}s ({sz_mb/max(0.01, t_copy):.1f} MB/s)")

    # 2. Hardware-accelerated candidate frame extraction
    t_scan_start = time.time()
    out_pattern = str(output_dir / f"day{day_num:02d}_{clip_stem[:25]}_cand_%04d.jpg")
    
    cmd = [
        "ffmpeg", "-y",
        "-hwaccel", "d3d11va",
        "-i", str(staged_clip),
        "-vf", f"fps=1,crop={CROP_W}:{CROP_H}:{CROP_X}:{CROP_Y},select='gt(scene\\,{SCENE_THRESH})'",
        "-fps_mode", "vfr",
        "-q:v", "3",
        out_pattern
    ]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        logger.warning(f"  FFmpeg timed out on {fname}, killing process...")
        proc = None
    except Exception as e:
        logger.error(f"  FFmpeg error on {fname}: {e}")
        proc = None

    t_scan = time.time() - t_scan_start

    # 3. Prune staged video immediately from SSD buffer
    if staged_clip.exists():
        try:
            staged_clip.unlink()
        except Exception:
            pass

    # 4. Count extracted candidate frames for this clip
    cand_files = list(output_dir.glob(f"day{day_num:02d}_{clip_stem[:25]}_cand_*.jpg"))
    cand_count = len(cand_files)
    
    logger.info(f"  Completed in {t_scan:.2f}s -> {cand_count} candidate frames staged.")
    return {
        "file": fname,
        "status": "success",
        "candidates": cand_count,
        "copy_sec": round(t_copy, 2),
        "scan_sec": round(t_scan, 2)
    }


def process_day(day_num: int, input_base: Path, output_base: Path, staging_base: Path) -> dict:
    in_day_dir = input_base / str(day_num)
    if not in_day_dir.exists():
        logger.warning(f"Day directory {in_day_dir} does not exist!")
        return {}

    out_day_dir = output_base / f"day_{day_num:02d}"
    out_day_dir.mkdir(parents=True, exist_ok=True)
    staging_base.mkdir(parents=True, exist_ok=True)

    clips = sorted(list(in_day_dir.glob("*.mp4")))
    total_clips = len(clips)
    logger.info(f"=== Scanning Day {day_num:02d}: {total_clips} clips found in {in_day_dir} ===")

    day_t0 = time.time()
    clip_results = []
    total_candidates = 0

    for idx, clip in enumerate(clips, 1):
        res = process_clip(clip, staging_base, out_day_dir, day_num, idx, total_clips)
        clip_results.append(res)
        total_candidates += res["candidates"]

    day_elapsed = time.time() - day_t0
    logger.info(f"=== Day {day_num:02d} Finished: {total_candidates} candidates in {day_elapsed/60:.2f} mins ===")

    manifest = {
        "day": day_num,
        "total_clips": total_clips,
        "total_candidates": total_candidates,
        "elapsed_seconds": round(day_elapsed, 2),
        "crop_offset": {"x": CROP_X, "y": CROP_Y, "w": CROP_W, "h": CROP_H},
        "clip_details": clip_results
    }

    with open(out_day_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return manifest


def main():
    parser = argparse.ArgumentParser(description="Industrial CCTV Fast Rolling Candidate Scanner")
    parser.add_argument("--start-day", type=int, default=1, help="Start day (default: 1)")
    parser.add_argument("--end-day", type=int, default=2, help="End day (default: 2)")
    parser.add_argument("--input-dir", type=str, default=r"E:\RO WATER SEP", help="External HDD root")
    parser.add_argument("--output-dir", type=str, default=r"D:\facial\data\stage1_candidates", help="Candidates output")
    parser.add_argument("--staging-dir", type=str, default=r"D:\facial\data\staging_buffer", help="NVMe SSD staging buffer")
    args = parser.parse_args()

    input_base = Path(args.input_dir)
    output_base = Path(args.output_dir)
    staging_base = Path(args.staging_dir)

    print("=" * 70)
    print("STAGE 1: ROLLING CANDIDATE SCANNER")
    print(f"Days {args.start_day} to {args.end_day} | Input: {input_base} | Output: {output_base}")
    print("=" * 70)

    total_start = time.time()
    all_days = []

    for d in range(args.start_day, args.end_day + 1):
        d_res = process_day(d, input_base, output_base, staging_base)
        if d_res:
            all_days.append(d_res)

    tot_elapsed = time.time() - total_start
    tot_cand = sum(d["total_candidates"] for d in all_days)

    summary_file = output_base / f"summary_days_{args.start_day}_to_{args.end_day}.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(all_days, f, indent=2)

    print("\n" + "=" * 70)
    print("STAGE 1 ROLLING SCAN COMPLETED")
    print(f"Days Processed:    {len(all_days)}")
    print(f"Total Candidates:  {tot_cand}")
    print(f"Total Wall-Clock:  {tot_elapsed/60:.2f} minutes")
    print(f"Summary JSON:      {summary_file}")
    print("=" * 70)


if __name__ == "__main__":
    main()

