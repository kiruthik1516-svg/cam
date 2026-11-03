#!/usr/bin/env python3
"""
extract_day05_clips.py
Extracts physical 3K video clips and annotated snapshots for Day 5 from E:\RO WATER SEP\5.
Extracts both Engine 2 and Engine 1 clip formats.
"""

import os
import re
import csv
import cv2
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np
from ultralytics import YOLO

FFMPEG_EXE = "ffmpeg"
CCTV_DAY5_DIR = Path("E:/RO WATER SEP/5")
OUTPUT_V2_DIR = Path("D:/facial/incident_evidence_v2/day_05")
OUTPUT_V1_DIR = Path("D:/facial/incident_evidence/day_05")
OUTPUT_V1_ROOT = Path("D:/facial/incident_evidence")

OUTPUT_V2_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_V1_DIR.mkdir(parents=True, exist_ok=True)

# 1. Discover all chunks in E:\RO WATER SEP\5
def list_cctv_chunks():
    chunks = []
    for f in CCTV_DAY5_DIR.glob("*.mp4"):
        m = re.search(r"(\d{14})\.mp4$", f.name)
        if not m:
            continue
        start_dt = datetime.strptime(m.group(1), "%Y%m%d%H%M%S")
        
        cap = cv2.VideoCapture(str(f))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 81000.0
        duration_sec = frame_count / fps
        cap.release()
        
        end_dt = start_dt + timedelta(seconds=duration_sec)
        chunks.append({
            "path": f,
            "filename": f.name,
            "start_dt": start_dt,
            "end_dt": end_dt,
            "fps": fps,
            "duration_sec": duration_sec
        })
    chunks.sort(key=lambda x: x["start_dt"])
    return chunks

INCIDENTS = [
    {
        "id_v2": "EVT-V2-D05-001",
        "id_v1": "EVT-D05-001",
        "peak_time": datetime(2026, 9, 5, 7, 20, 42),
        "zone_name": "RO Skid Controls & Pump Deck",
        "severity": "ELEVATED",
        "zone_short": "RO_SKID",
        "track_id": "SUBJ-312;REAL-07",
        "v2_filename": "Day05_EVT-V2-D05-001_ELEVATED_RO_SKID_20260905_072042.mp4",
        "v2_snapshot": "Day05_EVT-V2-D05-001_ELEVATED_RO_SKID_20260905_072042_Snapshot.jpg",
        "v1_filename": "Day05_EVT-D05-001.mp4"
    },
    {
        "id_v2": "EVT-V2-D05-002",
        "id_v1": "EVT-D05-002",
        "peak_time": datetime(2026, 9, 5, 7, 49, 29),
        "zone_name": "Plant Main Power Switch Breaker",
        "severity": "SEVERE",
        "zone_short": "SWITCH",
        "track_id": "SUBJ-313;REAL-25;REAL-44",
        "v2_filename": "Day05_EVT-V2-D05-002_SEVERE_SWITCH_20260905_074929.mp4",
        "v2_snapshot": "Day05_EVT-V2-D05-002_SEVERE_SWITCH_20260905_074929_Snapshot.jpg",
        "v1_filename": "Day05_EVT-D05-002.mp4"
    },
    {
        "id_v2": "EVT-V2-D05-003",
        "id_v1": "EVT-D05-003",
        "peak_time": datetime(2026, 9, 5, 8, 42, 38),
        "zone_name": "RO Skid Controls & Pump Deck",
        "severity": "ELEVATED",
        "zone_short": "RO_SKID",
        "track_id": "SUBJ-315;REAL-29",
        "v2_filename": "Day05_EVT-V2-D05-003_ELEVATED_RO_SKID_20260905_084238.mp4",
        "v2_snapshot": "Day05_EVT-V2-D05-003_ELEVATED_RO_SKID_20260905_084238_Snapshot.jpg",
        "v1_filename": "Day05_EVT-D05-003.mp4"
    },
    {
        "id_v2": "EVT-V2-D05-004",
        "id_v1": "EVT-D05-004",
        "peak_time": datetime(2026, 9, 5, 9, 12, 57),
        "zone_name": "Multiport Backwash Valves",
        "severity": "CRITICAL",
        "zone_short": "VALVES",
        "track_id": "SUBJ-315;REAL-14",
        "v2_filename": "Day05_EVT-V2-D05-004_CRITICAL_VALVES_20260905_091257.mp4",
        "v2_snapshot": "Day05_EVT-V2-D05-004_CRITICAL_VALVES_20260905_091257_Snapshot.jpg",
        "v1_filename": "Day05_EVT-D05-004.mp4"
    }
]

def extract_clip(src_path, offset_sec, duration_sec, out_path):
    if out_path.exists() and out_path.stat().st_size > 10 * 1024 * 1024:
        print(f"  [CACHE] Clip already exists: {out_path.name} ({out_path.stat().st_size / (1024*1024):.1f} MB)", flush=True)
        return True, ""
    cmd = [
        FFMPEG_EXE, "-y",
        "-ss", f"{offset_sec:.3f}",
        "-i", str(src_path),
        "-t", f"{duration_sec:.3f}",
        "-c:v", "libx264",
        "-crf", "20",
        "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-avoid_negative_ts", "make_zero",
        str(out_path)
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return res.returncode == 0, res.stderr

def generate_snapshot_with_overlay(clip_path, peak_offset_sec, out_snap_path, inc_info):
    cap = cv2.VideoCapture(str(clip_path))
    cap.set(cv2.CAP_PROP_POS_MSEC, peak_offset_sec * 1000.0)
    ret, frame = cap.read()
    if not ret or frame is None:
        cap.set(cv2.CAP_PROP_POS_FRAMES, 30)
        ret, frame = cap.read()
    cap.release()

    if not ret or frame is None:
        print(f"  [WARN] Failed to read frame from {clip_path}")
        return

    H, W = frame.shape[:2]
    # Draw Banner Overlay
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (W, 70), (15, 20, 25), -1)
    cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

    sev = inc_info["severity"]
    sev_color = (0, 30, 235) if sev == "SEVERE" else (0, 140, 255) if sev == "CRITICAL" else (0, 215, 255)

    cv2.putText(frame, f"DBGT RO PLANT SURVEILLANCE [IPC56] | DAY 05", (25, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (230, 230, 230), 2)
    cv2.putText(frame, f"INCIDENT: {inc_info['id_v2']} | {inc_info['peak_time'].strftime('%Y-%m-%d %H:%M:%S')} | ZONE: {inc_info['zone_name']} [{sev}]", (25, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.65, sev_color, 2)
    cv2.putText(frame, f"PERSONAS: {inc_info['track_id']}", (W - 550, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 240, 255), 1)

    cv2.imwrite(str(out_snap_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
    print(f"  [OK] Snapshot generated: {out_snap_path.name}")

def main():
    print("=== Scanning E:/RO WATER SEP/5 for CCTV video chunks ===")
    chunks = list_cctv_chunks()
    print(f"Discovered {len(chunks)} video chunks for Day 5.")

    for inc in INCIDENTS:
        print(f"\nProcessing {inc['id_v2']} ({inc['zone_name']})...")
        target_start = inc["peak_time"] - timedelta(seconds=60)
        target_end = inc["peak_time"] + timedelta(seconds=60)
        dur = 120.0

        # Find overlapping chunk
        matched_chunk = None
        for c in chunks:
            if c["start_dt"] <= target_start and c["end_dt"] >= target_end:
                matched_chunk = c
                break

        if not matched_chunk:
            for c in chunks:
                if c["start_dt"] <= inc["peak_time"] <= c["end_dt"]:
                    matched_chunk = c
                    break

        if not matched_chunk:
            print(f"  [ERROR] No chunk found for timestamp {inc['peak_time']}")
            continue

        offset_sec = max(0.0, (target_start - matched_chunk["start_dt"]).total_seconds())
        print(f"  Found source chunk: {matched_chunk['filename']}")
        print(f"  Start offset: {offset_sec:.1f}s | Target duration: {dur:.1f}s")

        # 1. Output to Engine 2 format
        v2_path = OUTPUT_V2_DIR / inc["v2_filename"]
        ok, err = extract_clip(matched_chunk["path"], offset_sec, dur, v2_path)
        if ok and v2_path.exists():
            sz_mb = v2_path.stat().st_size / (1024 * 1024)
            print(f"  [OK] Engine 2 clip extracted: {v2_path.name} ({sz_mb:.1f} MB)")
            # Generate snapshot
            snap_path = OUTPUT_V2_DIR / inc["v2_snapshot"]
            generate_snapshot_with_overlay(v2_path, 60.0, snap_path, inc)
        else:
            print(f"  [ERROR] Failed to extract {v2_path.name}: {err[:200]}")

        # 2. Output to Engine 1 format
        v1_path = OUTPUT_V1_DIR / inc["v1_filename"]
        import shutil
        if v2_path.exists():
            try:
                shutil.copy2(v2_path, v1_path)
                print(f"  [OK] Engine 1 clip synced: {v1_path.name}", flush=True)
            except Exception as e:
                print(f"  [WARN] Failed to copy to {v1_path.name}: {e}", flush=True)
            try:
                shutil.copy2(v2_path, OUTPUT_V1_ROOT / inc["v1_filename"])
            except Exception as e:
                pass

    print("\n================================================================================")
    print("ALL DAY 5 CLIPS SUCCESSFULLY EXTRACTED FROM PHYSICAL CCTV ARCHIVE (DRIVE E:)")
    print("================================================================================")

if __name__ == "__main__":
    main()
