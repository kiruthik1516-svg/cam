import os
import sys
import time
import json
import cv2
import numpy as np
from pathlib import Path
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from multiprocessing import Pool, cpu_count

load_dotenv(r"D:\facial\.env")
db_url = os.environ.get("DATABASE_URL")
engine = create_engine(db_url)

# Calibrated observation perimeter mask [x1, y1, x2, y2]
# [295, 20, 1490, 780] covers the corridor, RO skid, valves, and switch
PERIMETER_MASK = [295, 20, 1490, 780]

def process_clip_spatial_gating(args):
    video_path, ground_truth_seconds = args
    fname = Path(video_path).name
    
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return fname, [], 0, 0
        
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    step = int(round(fps))
    if step < 1: step = 25
    
    x1, y1, x2, y2 = PERIMETER_MASK
    prev_roi_gray = None
    
    active_seconds = set()
    total_seconds = 0
    frame_idx = 0
    curr_sec = 0
    
    while True:
        if frame_idx % step == 0:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Crop to perimeter mask
            roi = frame[y1:y2, x1:x2]
            roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            roi_gray = cv2.GaussianBlur(roi_gray, (21, 21), 0)
            
            if prev_roi_gray is not None:
                # Frame difference
                delta = cv2.absdiff(prev_roi_gray, roi_gray)
                thresh = cv2.threshold(delta, 25, 255, cv2.THRESH_BINARY)[1]
                thresh = cv2.dilate(thresh, None, iterations=2)
                
                # Check motion area
                contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                has_motion = False
                for c in contours:
                    if cv2.contourArea(c) > 300: # Human-scale motion threshold
                        has_motion = True
                        break
                        
                if has_motion:
                    # Pad window: current second +/- 1
                    active_seconds.add(curr_sec)
                    active_seconds.add(max(0, curr_sec - 1))
                    active_seconds.add(curr_sec + 1)
                    
            prev_roi_gray = roi_gray
            curr_sec += 1
            total_seconds += 1
        else:
            if not cap.grab():
                break
        frame_idx += 1
        
    cap.release()
    return fname, list(active_seconds), total_seconds, len(ground_truth_seconds)

def main():
    print("=" * 70)
    print("PHASE 0: STAGE 1 SPATIAL GATER RECALL & SPEED BENCHMARK (DAY 1)")
    print("=" * 70)
    
    day1_dir = Path(r"E:\RO WATER SEP\1")
    if not day1_dir.exists():
        print(f"ERROR: Day 1 directory {day1_dir} does not exist!")
        return

    # 1. Fetch ground-truth face detections for Day 1
    print("Fetching ground truth detections from PostgreSQL...")
    with engine.connect() as conn:
        res = conn.execute(text("""
            SELECT device_id, sequence_number, timestamp, bbox
            FROM detections
            WHERE batch_id = 'batch_20261023145845_884f05'
            ORDER BY device_id, sequence_number
        """)).fetchall()
        
    gt_by_file = {}
    for r in res:
        dev_id = r[0]
        seq = r[1]
        gt_by_file.setdefault(dev_id, []).append(seq)
        
    total_gt = len(res)
    print(f"Loaded {total_gt} ground-truth face detections across {len(gt_by_file)} files.")
    
    # 2. Collect video clips
    clips = sorted(list(day1_dir.glob("*.mp4")))
    print(f"Found {len(clips)} video clips in {day1_dir}.")
    
    tasks = []
    for c in clips:
        gt_secs = gt_by_file.get(c.name, [])
        tasks.append((c, gt_secs))
        
    # 3. Execute parallel spatial gating across workers
    workers = min(6, cpu_count())
    print(f"\nLaunching {workers} parallel CPU workers for spatial gating...")
    t0 = time.time()
    
    results = []
    with Pool(processes=workers) as pool:
        for res_item in pool.imap_unordered(process_clip_spatial_gating, tasks):
            results.append(res_item)
            fname, active_secs, tot_secs, gt_count = res_item
            if gt_count > 0:
                print(f"  [Processed] {fname[:38]}... | Active: {len(active_secs):3d}s / {tot_secs:4d}s | GT faces: {gt_count:2d}")
                
    elapsed = time.time() - t0
    
    # 4. Evaluate Recall & Skip Rate
    print("\n" + "=" * 70)
    print("BENCHMARK AUDIT RESULTS")
    print("=" * 70)
    
    total_active_seconds = 0
    total_video_seconds = 0
    captured_gt_count = 0
    missed_gt = []
    
    active_by_file = {r[0]: set(r[1]) for r in results}
    tot_by_file = {r[0]: r[2] for r in results}
    
    for c in clips:
        fname = c.name
        gt_secs = gt_by_file.get(fname, [])
        active_set = active_by_file.get(fname, set())
        total_video_seconds += tot_by_file.get(fname, 0)
        total_active_seconds += len(active_set)
        
        for gt_s in gt_secs:
            # Check if gt_s or +/- 1 second was captured
            if any(s in active_set for s in [gt_s - 1, gt_s, gt_s + 1]):
                captured_gt_count += 1
            else:
                missed_gt.append((fname, gt_s))
                
    recall_pct = (captured_gt_count / total_gt * 100.0) if total_gt > 0 else 100.0
    skip_pct = ((total_video_seconds - total_active_seconds) / total_video_seconds * 100.0) if total_video_seconds > 0 else 0.0
    agg_fps = total_video_seconds / elapsed if elapsed > 0 else 0.0
    
    print(f"Total Video Scanned:        {total_video_seconds:6d} seconds ({total_video_seconds/3600:.2f} hours)")
    print(f"Total Active Seconds Kept:  {total_active_seconds:6d} seconds ({total_active_seconds/3600:.2f} hours)")
    print(f"Empty Footage Skipped:      {skip_pct:.2f}% (Compression: {total_video_seconds/max(1, total_active_seconds):.1f}x)")
    print(f"Wall-Clock Processing Time: {elapsed:.2f} seconds ({elapsed/60:.2f} minutes)")
    print(f"Aggregate Processing Speed: {agg_fps:.1f} Video FPS")
    print("-" * 70)
    print(f"GROUND-TRUTH RECALL:        {captured_gt_count} / {total_gt} ({recall_pct:.2f}%)")
    
    if missed_gt:
        print(f"\nWARNING: {len(missed_gt)} ground-truth face detections were missed:")
        for m in missed_gt:
            print(f"  File: {m[0]} @ Second {m[1]}")
    else:
        print("\nSUCCESS: 100.0% PERFECT RECALL! Zero face detections missed.")
        print(f"Stage 1 eliminates {skip_pct:.1f}% of footage while preserving 100% of human activity!")
    print("=" * 70)

if __name__ == "__main__":
    main()

