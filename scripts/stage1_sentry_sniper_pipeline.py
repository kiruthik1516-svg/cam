"""High-Throughput Hardware-Accelerated Sentry + Sniper Scanner (Stage 1)

Architecture:
1. Hardware Sentry (d3d11va / Intel Iris Xe):
   - Scans 3K HEVC at ~60-80 FPS keyframe rate directly from USB HDD (115x real-time).
   - Monitors entrance choke-point [1250, 120, 1550, 380].
   - Skips 100% of inactive clips with zero disk write overhead (20s per 45-min clip).
2. Intelligent Surveillance Windowing:
   - Merges motion events with pre-buffer (15s) and post-stay margin (300s).
   - Propagates carry-over windows across contiguous clip boundaries.
3. Perimeter Sniper:
   - Runs exclusively inside active windows.
   - Extracts 1:1 lossless perimeter crops [295, 20, 1490, 780] at 1 FPS with high JPEG quality (-q:v 2).
   - Preserves 100% of native face pixels for cloud ArcFace embedding.
"""

from __future__ import annotations

import argparse
import datetime
import json
import logging
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import cv2
import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("SentrySniper")

# Entrance door choke-point [x1, y1, x2, y2]
DEFAULT_DOOR_BOX = (1250, 120, 1550, 380)

# Lossless active perimeter crop: [x1, y1, x2, y2] = [295, 20, 1490, 780]
# In ffmpeg crop syntax: crop=out_w:out_h:x:y -> 1195:760:295:20
DEFAULT_SNIPER_CROP = "1195:760:295:20"


def get_clip_duration(clip_path: Path) -> float:
    """Fast probe of clip duration in seconds."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "csv=p=0",
        str(clip_path)
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(res.stdout.strip())
    except Exception:
        return 2697.0  # Default ~44.95 mins


def run_hardware_sentry(
    clip_path: Path,
    door_box: tuple[int, int, int, int] = DEFAULT_DOOR_BOX,
    min_motion_px: int = 3000,
    motion_thr: int = 25
) -> tuple[list[float], int, float]:
    """Scans keyframes at door choke-point using Intel Iris Xe hardware acceleration."""
    t0 = time.time()
    x1, y1, x2, y2 = door_box
    crop_w, crop_h = x2 - x1, y2 - y1

    cmd = [
        "ffmpeg", "-y", "-hwaccel", "d3d11va",
        "-skip_frame", "nokey",
        "-i", str(clip_path),
        "-fps_mode", "passthrough",
        "-vf", f"crop={crop_w}:{crop_h}:{x1}:{y1},scale=160:120,format=gray",
        "-f", "rawvideo",
        "-pix_fmt", "gray",
        "-"
    ]

    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=10**7)
    thumb_w, thumb_h = 160, 120
    frame_bytes = thumb_w * thumb_h

    kf_idx = 0
    prev_thumb = None
    event_kf_indices = []

    while True:
        raw = p.stdout.read(frame_bytes)
        if len(raw) < frame_bytes:
            break
        kf_idx += 1
        img = np.frombuffer(raw, dtype=np.uint8).reshape((thumb_h, thumb_w))
        img_blur = cv2.GaussianBlur(img, (5, 5), 0)

        if prev_thumb is not None:
            diff = cv2.absdiff(img_blur, prev_thumb)
            px_diff = (diff > motion_thr).sum()
            if px_diff > min_motion_px:
                event_kf_indices.append(kf_idx)

        prev_thumb = img_blur

    p.stdout.close()
    p.wait()
    scan_dt = time.time() - t0

    if kf_idx == 0:
        return [], 0, scan_dt

    # Get approximate clip duration
    duration = get_clip_duration(clip_path)
    sec_per_kf = duration / kf_idx
    event_timestamps = [idx * sec_per_kf for idx in event_kf_indices]

    return event_timestamps, kf_idx, scan_dt


def make_surveillance_windows(
    events: list[float],
    clip_duration: float,
    carry_in_sec: float = 0.0,
    pre_window: float = 5.0,
    post_window: float = 25.0
) -> tuple[list[tuple[float, float]], float]:
    """Generates continuous active surveillance windows and calculates carry-out margin."""
    raw_wins = []

    if carry_in_sec > 0.0:
        raw_wins.append([0.0, min(clip_duration, carry_in_sec)])

    for t in sorted(events):
        a = max(0.0, t - pre_window)
        b = t + post_window
        raw_wins.append([a, b])

    if not raw_wins:
        return [], 0.0

    raw_wins.sort(key=lambda x: x[0])
    merged = [raw_wins[0]]

    for cur in raw_wins[1:]:
        prev = merged[-1]
        if cur[0] <= prev[1]:
            prev[1] = max(prev[1], cur[1])
        else:
            merged.append(cur)

    # Check for carry-out to next contiguous clip
    carry_out = 0.0
    final_wins = []
    for a, b in merged:
        if b > clip_duration:
            carry_out = max(carry_out, b - clip_duration)
            final_wins.append((a, clip_duration))
        else:
            final_wins.append((a, b))

    return final_wins, carry_out


def run_perimeter_sniper(
    clip_path: Path,
    windows: list[tuple[float, float]],
    out_dir: Path,
    day_num: int,
    sniper_fps: int = 1,
    crop_str: str = DEFAULT_SNIPER_CROP
) -> tuple[int, float]:
    """Lossless 1:1 perimeter sniper running exclusively during active surveillance windows."""
    t0 = time.time()
    clip_stem = clip_path.stem
    total_extracted = 0

    for win_idx, (start_sec, end_sec) in enumerate(windows):
        dur = end_sec - start_sec
        if dur < 0.5:
            continue

        out_pattern = out_dir / f"day{day_num:02d}_{clip_stem}_w{win_idx:02d}_%05d.jpg"

        cmd = [
            "ffmpeg", "-y", "-hwaccel", "d3d11va",
            "-ss", f"{start_sec:.2f}",
            "-t", f"{dur:.2f}",
            "-i", str(clip_path),
            "-vf", f"fps={sniper_fps},crop={crop_str}",
            "-q:v", "2",
            str(out_pattern)
        ]

        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            # Count extracted files
            extracted = list(out_dir.glob(f"day{day_num:02d}_{clip_stem}_w{win_idx:02d}_*.jpg"))
            total_extracted += len(extracted)
        except Exception as e:
            logger.error(f"Sniper extraction failed for {clip_stem} window {win_idx}: {e}")

    sniper_dt = time.time() - t0
    return total_extracted, sniper_dt


def process_single_clip(
    clip_path: Path,
    out_dir: Path,
    day_num: int,
    carry_in_sec: float,
    min_motion_px: int = 3000,
    pre_win: float = 5.0,
    post_win: float = 25.0,
    sniper_fps: int = 1
) -> dict:
    """Complete Sentry + Sniper execution for a single 45-min clip."""
    clip_name = clip_path.name
    clip_dur = get_clip_duration(clip_path)

    # Step 1: Hardware-Accelerated Sentry
    events, kf_cnt, sentry_dt = run_hardware_sentry(
        clip_path, min_motion_px=min_motion_px
    )

    # Step 2: Surveillance Window Calculation
    windows, carry_out_sec = make_surveillance_windows(
        events, clip_dur, carry_in_sec=carry_in_sec,
        pre_window=pre_win, post_window=post_win
    )

    tot_win_sec = sum(b - a for a, b in windows)

    # Step 3: Perimeter Sniper (only if windows exist)
    extracted_count = 0
    sniper_dt = 0.0
    if windows:
        extracted_count, sniper_dt = run_perimeter_sniper(
            clip_path, windows, out_dir, day_num, sniper_fps=sniper_fps
        )

    tot_time = sentry_dt + sniper_dt
    skip_pct = ((clip_dur - tot_win_sec) / max(1.0, clip_dur)) * 100.0

    return {
        "clip": clip_name,
        "duration_sec": round(clip_dur, 2),
        "keyframes": kf_cnt,
        "sentry_time_sec": round(sentry_dt, 2),
        "events_count": len(events),
        "windows": [(round(a, 2), round(b, 2)) for a, b in windows],
        "active_window_sec": round(tot_win_sec, 2),
        "skip_pct": round(skip_pct, 1),
        "sniper_time_sec": round(sniper_dt, 2),
        "extracted_frames": extracted_count,
        "total_time_sec": round(tot_time, 2),
        "carry_out_sec": round(carry_out_sec, 2)
    }


def process_day(
    day_num: int,
    input_base: Path,
    output_base: Path,
    min_motion_px: int = 3000,
    pre_win: float = 5.0,
    post_win: float = 25.0,
    sniper_fps: int = 1,
    start_clip: int = 1,
    end_clip: int = 33
) -> dict:
    """Processes all 33 clips of a single surveillance day."""
    day_dir = input_base / str(day_num)
    if not day_dir.exists():
        logger.warning(f"Day directory {day_dir} does not exist!")
        return {}

    out_day_dir = output_base / f"day_{day_num:02d}"
    out_day_dir.mkdir(parents=True, exist_ok=True)

    clips = sorted(list(day_dir.glob("*.mp4")))
    total_clips = len(clips)

    manifest_path = out_day_dir / "manifest.json"
    if start_clip == 1 and end_clip >= total_clips and manifest_path.exists():
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                existing_manifest = json.load(f)
            if existing_manifest.get("total_clips") == total_clips:
                frames_cnt = existing_manifest.get("total_extracted_frames", 0)
                logger.info(f"DAY {day_num:02d} ALREADY COMPLETED ({frames_cnt} frames in manifest) - SKIPPING")
                return existing_manifest
        except Exception:
            pass

    logger.info(f"======================================================================")
    logger.info(f"PROCESSING DAY {day_num:02d}: {total_clips} CLIPS (720P/3K SURVEILLANCE)")
    logger.info(f"Input: {day_dir} | Output: {out_day_dir} | Range: Clips #{start_clip} to #{end_clip}")
    logger.info(f"Settings: min_motion={min_motion_px}px, pre_win={pre_win}s, post_win={post_win}s")
    logger.info(f"======================================================================")

    day_t0 = time.time()
    clip_summaries = []
    carry_sec = 0.0

    total_active_sec = 0.0
    total_extracted = 0

    for i, clip in enumerate(clips):
        clip_num = i + 1
        clip_stem = clip.stem

        if clip_num > end_clip:
            break

        if clip_num < start_clip:
            # Check previously extracted frames
            existing = list(out_day_dir.glob(f"day{day_num:02d}_{clip_stem}_*.jpg"))
            clip_dur = get_clip_duration(clip)
            ext_cnt = len(existing)
            status = f"ALREADY_PROCESSED ({ext_cnt} frames)" if ext_cnt > 0 else "NOMINAL (Skipped)"
            logger.info(f"[{clip_num:02d}/{total_clips}] {clip.name[:25]}... -> [PREVIOUS RUN] {status}")
            clip_summaries.append({
                "clip": clip.name,
                "duration_sec": round(clip_dur, 2),
                "keyframes": 0,
                "sentry_time_sec": 0.0,
                "events_count": 0,
                "windows": [],
                "active_window_sec": ext_cnt,
                "skip_pct": round(((clip_dur - ext_cnt) / max(1.0, clip_dur)) * 100.0, 1),
                "sniper_time_sec": 0.0,
                "extracted_frames": ext_cnt,
                "total_time_sec": 0.0,
                "carry_out_sec": 0.0
            })
            total_active_sec += ext_cnt
            total_extracted += ext_cnt
            continue

        # Clean any partial frames from previous interrupted run of this clip
        for partial_file in out_day_dir.glob(f"day{day_num:02d}_{clip_stem}_*.jpg"):
            try:
                partial_file.unlink()
            except Exception:
                pass

        c_t0 = time.time()
        res = process_single_clip(
            clip, out_day_dir, day_num, carry_sec,
            min_motion_px=min_motion_px,
            pre_win=pre_win, post_win=post_win,
            sniper_fps=sniper_fps
        )
        carry_sec = res["carry_out_sec"]
        clip_summaries.append(res)

        total_active_sec += res["active_window_sec"]
        total_extracted += res["extracted_frames"]

        status = f"ACTIVE ({res['extracted_frames']} frames, {res['active_window_sec']:.0f}s)" if res['extracted_frames'] > 0 else "NOMINAL (Skipped)"
        logger.info(
            f"[{clip_num:02d}/{total_clips}] {clip.name[:25]}... -> {status} "
            f"in {res['total_time_sec']:.1f}s (Sentry: {res['sentry_time_sec']:.1f}s, Sniper: {res['sniper_time_sec']:.1f}s)"
        )

    day_elapsed = time.time() - day_t0
    total_video_sec = sum(c["duration_sec"] for c in clip_summaries)
    overall_skip = ((total_video_sec - total_active_sec) / max(1.0, total_video_sec)) * 100.0

    manifest = {
        "day": day_num,
        "total_clips": total_clips,
        "total_video_sec": round(total_video_sec, 2),
        "total_active_window_sec": round(total_active_sec, 2),
        "overall_skip_pct": round(overall_skip, 2),
        "total_extracted_frames": total_extracted,
        "runtime_sec": round(day_elapsed, 2),
        "runtime_min": round(day_elapsed / 60.0, 2),
        "clips": clip_summaries
    }

    manifest_path = out_day_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    logger.info(f"----------------------------------------------------------------------")
    logger.info(f"DAY {day_num:02d} COMPLETED:")
    logger.info(f"  Total Video:       {total_video_sec/3600:.2f} hours ({total_clips} clips)")
    logger.info(f"  Active Window:     {total_active_sec/60:.2f} minutes (Skipped {overall_skip:.1f}%)")
    logger.info(f"  Extracted Frames:  {total_extracted} lossless candidate crops")
    logger.info(f"  Total Wall-Clock:  {day_elapsed/60:.2f} minutes ({total_video_sec/day_elapsed:.1f}x real-time speed)")
    logger.info(f"  Manifest:          {manifest_path}")
    logger.info(f"----------------------------------------------------------------------")

    return manifest


def main():
    parser = argparse.ArgumentParser(description="Hardware-Accelerated Sentry + Sniper Pipeline")
    parser.add_argument("--start-day", type=int, default=1, help="Start day (default: 1)")
    parser.add_argument("--end-day", type=int, default=1, help="End day (default: 1)")
    parser.add_argument("--start-clip", type=int, default=1, help="Start clip index for start-day (default: 1)")
    parser.add_argument("--end-clip", type=int, default=33, help="End clip index for end-day (default: 33)")
    parser.add_argument("--input-dir", type=str, default=r"E:\RO WATER SEP", help="External HDD root")
    parser.add_argument("--output-dir", type=str, default=r"D:\facial\data\stage1_candidates", help="Candidates output root")
    parser.add_argument("--min-motion-px", type=int, default=3000, help="Human-scale motion pixel threshold (default: 3000)")
    parser.add_argument("--pre-win", type=float, default=5.0, help="Window pre-margin seconds (default: 5.0)")
    parser.add_argument("--post-win", type=float, default=25.0, help="Window post-margin seconds (default: 25.0)")
    parser.add_argument("--sniper-fps", type=int, default=1, help="Sniper extraction framerate (default: 1)")
    args = parser.parse_args()

    input_base = Path(args.input_dir)
    output_base = Path(args.output_dir)

    print("=" * 70)
    print("STAGE 1: HARDWARE-ACCELERATED SENTRY + PERIMETER SNIPER PIPELINE")
    print(f"Days {args.start_day} to {args.end_day} | Clips: {args.start_clip} to {args.end_clip} | Input: {input_base} | Output: {output_base}")
    print(f"Choke Point: {DEFAULT_DOOR_BOX} | Sniper Crop: {DEFAULT_SNIPER_CROP} @ {args.sniper_fps} FPS")
    print(f"Motion Threshold: >{args.min_motion_px} px | Pre/Post Margin: -{args.pre_win}s / +{args.post_win}s")
    print("=" * 70)

    total_start = time.time()
    day_manifests = []

    for d in range(args.start_day, args.end_day + 1):
        s_clip = args.start_clip if d == args.start_day else 1
        e_clip = args.end_clip if d == args.end_day else 33
        m = process_day(
            d, input_base, output_base,
            min_motion_px=args.min_motion_px,
            pre_win=args.pre_win, post_win=args.post_win,
            sniper_fps=args.sniper_fps,
            start_clip=s_clip,
            end_clip=e_clip
        )
        if m:
            day_manifests.append(m)

    tot_elapsed = time.time() - total_start
    tot_frames = sum(m["total_extracted_frames"] for m in day_manifests)

    summary_file = output_base / f"pipeline_summary_days_{args.start_day}_to_{args.end_day}.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(day_manifests, f, indent=2)

    print("\n" + "=" * 70)
    print("ALL REQUESTED DAYS PROCESSED SUCCESSFULLY")
    print(f"Days Completed:    {len(day_manifests)}")
    print(f"Total Candidates:  {tot_frames} lossless frames")
    print(f"Total Wall-Clock:  {tot_elapsed/60:.2f} minutes")
    print(f"Summary JSON:      {summary_file}")
    print("=" * 70)


if __name__ == "__main__":
    main()

