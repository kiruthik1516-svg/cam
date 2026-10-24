import os
import sys
import time
import json
import cv2
import argparse
import numpy as np
from pathlib import Path
from multiprocessing import Pool, cpu_count

# Calibrated observation perimeter mask [x1, y1, x2, y2]
PERIMETER_MASK = [295, 20, 1490, 780]

def scan_single_clip(args):
    video_path, out_dir_str, day_num = args
    fname = Path(video_path).name
    out_dir = Path(out_dir_str)
    
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return fname, 0, 0, 0
        
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    step = int(round(fps))
    if step < 1: step = 25
    
    x1, y1, x2, y2 = PERIMETER_MASK
    prev_roi_gray = None
    
    total_sec = 0
    active_sec_count = 0
    frames_extracted = 0
    frame_idx = 0
    curr_sec = 0
    
    active_records = []
    
    while True:
        if frame_idx % step == 0:
            ret, frame = cap.read()
            if not ret:
                break
                
            roi = frame[y1:y2, x1:x2]
            roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            roi_gray = cv2.GaussianBlur(roi_gray, (21, 21), 0)
            
            if prev_roi_gray is not None:
                delta = cv2.absdiff(prev_roi_gray, roi_gray)
                thresh = cv2.threshold(delta, 25, 255, cv2.THRESH_BINARY)[1]
                thresh = cv2.dilate(thresh, None, iterations=2)
                
                contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                motion_boxes = []
                for c in contours:
                    if cv2.contourArea(c) > 300: # Human-scale motion
                        bx, by, bw, bh = cv2.boundingRect(c)
                        motion_boxes.append([x1 + bx, y1 + by, x1 + bx + bw, y1 + by + bh])
                        
                if motion_boxes:
                    active_sec_count += 1
                    # Save native 3K frame
                    out_name = f"day{day_num:02d}_{fname[:30]}_s{curr_sec:04d}.jpg"
                    out_path = out_dir / out_name
                    cv2.imwrite(str(out_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
                    frames_extracted += 1
                    active_records.append({
                        "file": fname,
                        "second": curr_sec,
                        "frame_image": out_name,
                        "motion_boxes": motion_boxes
                    })
                    
            prev_roi_gray = roi_gray
            curr_sec += 1
            total_sec += 1
        else:
            if not cap.grab():
                break
        frame_idx += 1
        
    cap.release()
    return fname, total_sec, active_sec_count, frames_extracted, active_records

def process_day(day_num, base_in_dir, base_out_dir, workers):
    in_day_dir = Path(base_in_dir) / str(day_num)
    out_day_dir = Path(base_out_dir) / f"day_{day_num:02d}"
    out_day_dir.mkdir(parents=True, exist_ok=True)
    
    clips = sorted(list(in_day_dir.glob("*.mp4")))
    if not clips:
        print(f"No clips found for Day {day_num} in {in_day_dir}")
        return
        
    print(f"\n--- Scanning Day {day_num:02d} ({len(clips)} files) ---")
    tasks = [(c, str(out_day_dir), day_num) for c in clips]
    
    t0 = time.time()
    total_sec_all = 0
    active_sec_all = 0
    extracted_all = 0
    all_manifest = []
    
    with Pool(processes=workers) as pool:
        for res in pool.imap_unordered(scan_single_clip, tasks):
            fname, tot_s, act_s, ext_cnt, recs = res
            total_sec_all += tot_s
            active_sec_all += act_s
            extracted_all += ext_cnt
            all_manifest.extend(recs)
            if ext_cnt > 0:
                print(f"  [Active] {fname[:35]}... -> {ext_cnt} candidate frames ({act_s}s active / {tot_s}s)")
                
    elapsed = time.time() - t0
    skip_pct = ((total_sec_all - active_sec_all) / max(1, total_sec_all)) * 100.0
    
    # Write day manifest
    with open(out_day_dir / "manifest.json", "w") as f:
        json.dump(all_manifest, f, indent=2)
        
    print(f"Day {day_num:02d} Completed in {elapsed:.1f}s ({elapsed/60:.2f}m) | Video: {total_sec_all/3600:.1f}h | Active Frames: {extracted_all} | Skipped: {skip_pct:.1f}%")
    return {
        "day": day_num,
        "clips": len(clips),
        "total_seconds": total_sec_all,
        "active_seconds": active_sec_all,
        "extracted_frames": extracted_all,
        "skip_pct": skip_pct,
        "runtime_sec": elapsed
    }

def main():
    parser = argparse.ArgumentParser(description="Stage 1 Fast Spatial ROI Gater for Industrial Rooftop Surveillance")
    parser.add_argument("--start-day", type=int, default=2, help="Start day folder number (default: 2)")
    parser.add_argument("--end-day", type=int, default=30, help="End day folder number (default: 30)")
    parser.add_argument("--input-dir", type=str, default=r"E:\RO WATER SEP", help="Source directory containing day folders")
    parser.add_argument("--output-dir", type=str, default=r"D:\facial\data\stage1_candidates", help="Staging output directory")
    parser.add_argument("--workers", type=int, default=min(6, cpu_count()), help="Number of parallel worker processes")
    args = parser.parse_args()
    
    base_out = Path(args.output_dir)
    base_out.mkdir(parents=True, exist_ok=True)
    
    print("=" * 70)
    print("STAGE 1: FAST SPATIAL ROI GATER FOR 30-DAY INDUSTRIAL AUDIT")
    print(f"Range: Days {args.start_day} to {args.end_day} | Input: {args.input_dir} | Output: {args.output_dir}")
    print(f"Parallel Worker Processes: {args.workers}")
    print("=" * 70)
    
    total_start = time.time()
    day_summaries = []
    
    for day in range(args.start_day, args.end_day + 1):
        day_res = process_day(day, args.input_dir, args.output_dir, args.workers)
        if day_res:
            day_summaries.append(day_res)
            
    total_time = time.time() - total_start
    with open(base_out / "overall_summary.json", "w") as f:
        json.dump(day_summaries, f, indent=2)
        
    tot_frames = sum(d["extracted_frames"] for d in day_summaries)
    tot_sec = sum(d["total_seconds"] for d in day_summaries)
    avg_skip = np.mean([d["skip_pct"] for d in day_summaries]) if day_summaries else 0.0
    
    print("\n" + "=" * 70)
    print("STAGE 1 SCAN COMPLETED SUCCESSFULLY")
    print(f"Total Days Processed: {len(day_summaries)}")
    print(f"Total Video Scanned:  {tot_sec/3600:.1f} hours")
    print(f"Total Frames Staged:  {tot_frames} Native 3K Frames")
    print(f"Average Empty Skip:   {avg_skip:.2f}%")
    print(f"Total Scan Runtime:   {total_time/60:.2f} minutes")
    print("=" * 70)

if __name__ == "__main__":
    main()

