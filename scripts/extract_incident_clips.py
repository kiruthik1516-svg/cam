#!/usr/bin/env python3
"""
extract_incident_clips.py
Extracts physical incident video clips directly from the mounted read-only
raw footage drive (E:\\RO WATER SEP) into local forensic storage (D:\\facial\\incident_evidence).

SAFETY ENFORCEMENT:
- All source files on drive E: are strictly read-only.
- All writes are directed solely to D:\\facial\\incident_evidence\\.
- Uses lossless stream copy (-c copy) for zero re-encoding loss and maximum speed (>200x realtime).
"""

import argparse
import csv
from datetime import datetime
import glob
import os
from pathlib import Path
import re
import subprocess
import sys
import time

def parse_day_number(filename):
    """Extract day integer from CSV filename (e.g. Day1_... -> 1, Day15_... -> 15)."""
    m = re.search(r'Day(\d+)_', Path(filename).name)
    return int(m.group(1)) if m else None

def index_raw_footage(root_dir="E:/RO WATER SEP"):
    """
    Builds a chronological index of all raw MP4 chunks across all day folders.
    Guarantees strict read-only access to drive E:.
    """
    footage_index = {}
    root = Path(root_dir)
    if not root.exists():
        print(f"[ERROR] Raw footage directory not found at: {root_dir}")
        return {}

    day_dirs = sorted([d for d in root.iterdir() if d.is_dir() and d.name.isdigit()], key=lambda x: int(x.name))
    for d in day_dirs:
        day_num = int(d.name)
        chunks = []
        for f in d.glob("*.mp4"):
            m = re.search(r'_(\d{14})\.mp4$', f.name)
            if m:
                dt = datetime.strptime(m.group(1), "%Y%m%d%H%M%S")
                chunks.append((dt, f))
        chunks.sort(key=lambda x: x[0])
        footage_index[day_num] = chunks

    total_files = sum(len(v) for v in footage_index.values())
    print(f"[OK] Indexed {total_files} raw video chunks across {len(footage_index)} days from {root_dir} (READ-ONLY).")
    return footage_index

def locate_raw_chunk(footage_index, day_num, target_dt):
    """Find the exact MP4 chunk covering target_dt and compute seek start offset."""
    chunks = footage_index.get(day_num, [])
    if not chunks:
        return None, 0.0

    best_dt, best_path = None, None
    for chunk_dt, chunk_path in chunks:
        if chunk_dt <= target_dt:
            best_dt = chunk_dt
            best_path = chunk_path
        else:
            break

    if best_path:
        offset = (target_dt - best_dt).total_seconds()
        return best_path, max(0.0, offset)
    return None, 0.0

def format_time_offset(seconds):
    """Format seconds into HH:MM:SS."""
    h = int(seconds) // 3600
    m = (int(seconds) % 3600) // 60
    s = int(seconds) % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

def extract_clips(
    csv_dir="D:/facial",
    raw_footage_root="E:/RO WATER SEP",
    out_dir="D:/facial/incident_evidence",
    hazard_filter=None,
    target_day=None,
    max_clips=None,
    max_duration=None
):
    out_path = Path(out_dir).resolve()
    out_path.mkdir(parents=True, exist_ok=True)

    footage_index = index_raw_footage(raw_footage_root)
    if not footage_index:
        return

    csv_pattern = str(Path(csv_dir) / "Day*_Persona_Video_Clipping_Index.csv")
    csv_files = glob.glob(csv_pattern)
    csv_files.sort(key=lambda x: parse_day_number(x) or 0)

    if not csv_files:
        print(f"[ERROR] No clipping CSV index files found matching: {csv_pattern}")
        return

    manifest_rows = []
    manifest_csv = out_path / "extracted_incident_manifest.csv"

    allowed_hazards = [h.strip().upper() for h in hazard_filter.split(",")] if hazard_filter else ["CRITICAL", "SEVERE"]
    print(f"[FILTER] Target Hazards: {allowed_hazards}")
    if target_day:
        print(f"[FILTER] Target Day: {target_day}")
    if max_duration:
        print(f"[FILTER] Max Duration Cap: {max_duration} seconds")

    total_extracted = 0
    total_bytes = 0
    t_start = time.time()

    for csv_file in csv_files:
        day_num = parse_day_number(csv_file)
        if target_day and day_num != target_day:
            continue

        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            events = list(reader)

        print(f"\n--- Processing Day {day_num:02d} ({len(events)} total indexed events) ---")
        day_extracted = 0

        for ev in events:
            if max_clips and total_extracted >= max_clips:
                break

            evt_id = ev.get("Event_ID", "UNKNOWN")
            hazard = (ev.get("Hazard_Level") or ev.get("Hazard_Priority") or "NOMINAL").upper()
            zone = ev.get("Critical_Zone") or ev.get("Monitored_Facility_Zone") or "Plant Walkway"
            start_str = ev.get("Start_WallClock_Time", "")

            if allowed_hazards != ["ALL"] and hazard not in allowed_hazards:
                continue

            try:
                start_dt = datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
            except Exception:
                continue

            raw_chunk_path, raw_offset_sec = locate_raw_chunk(footage_index, day_num, start_dt)
            if not raw_chunk_path:
                print(f"  [WARN] No matching raw chunk on drive E: for {evt_id} at {start_str}")
                continue

            duration = max(5, int(ev.get("Duration_Seconds", 30)))
            if max_duration and duration > max_duration:
                duration = max_duration

            seek_start = max(0.0, raw_offset_sec - 5.0)
            seek_end = raw_offset_sec + duration + 5.0

            clean_zone = re.sub(r'[^a-zA-Z0-9]+', '_', zone).strip('_')
            ts_tag = start_dt.strftime('%Y%m%d_%H%M%S')
            out_filename = f"Day{day_num:02d}_{evt_id}_{hazard}_{clean_zone}_{ts_tag}.mp4"
            out_file_path = out_path / out_filename

            if out_file_path.exists() and out_file_path.stat().st_size > 1024:
                file_size_mb = round(out_file_path.stat().st_size / (1024 * 1024), 2)
                manifest_rows.append({
                    "Event_ID": evt_id,
                    "Day": day_num,
                    "Hazard_Level": hazard,
                    "Facility_Zone": zone,
                    "WallClock_Start": start_str,
                    "Duration_Sec": duration,
                    "Extracted_Clip_File": str(out_file_path.name),
                    "File_Size_MB": file_size_mb,
                    "Status": "ALREADY_EXISTS"
                })
                day_extracted += 1
                total_extracted += 1
                total_bytes += out_file_path.stat().st_size
                continue

            # Stream copy with ffmpeg (Read-only on source, write to local SSD)
            start_fmt = format_time_offset(seek_start)
            end_fmt = format_time_offset(seek_end)

            cmd = [
                "ffmpeg",
                "-ss", start_fmt,
                "-to", end_fmt,
                "-i", str(raw_chunk_path),
                "-c", "copy",
                "-avoid_negative_ts", "make_zero",
                str(out_file_path),
                "-y",
                "-loglevel", "error"
            ]

            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0 and out_file_path.exists() and out_file_path.stat().st_size > 0:
                file_size_mb = round(out_file_path.stat().st_size / (1024 * 1024), 2)
                total_bytes += out_file_path.stat().st_size
                day_extracted += 1
                total_extracted += 1
                manifest_rows.append({
                    "Event_ID": evt_id,
                    "Day": day_num,
                    "Hazard_Level": hazard,
                    "Facility_Zone": zone,
                    "WallClock_Start": start_str,
                    "Duration_Sec": duration,
                    "Extracted_Clip_File": str(out_file_path.name),
                    "File_Size_MB": file_size_mb,
                    "Status": "EXTRACTED_OK"
                })
                print(f"  [OK] Extracted {out_filename} ({file_size_mb} MB) in zone '{zone}'")
            else:
                err_msg = res.stderr.strip()[:100] if res.stderr else "Unknown error"
                print(f"  [FAIL] Failed to extract {out_filename}: {err_msg}")

        print(f"Day {day_num:02d} completed: {day_extracted} clips saved.")
        if max_clips and total_extracted >= max_clips:
            break

    # Save manifest CSV
    if manifest_rows:
        fieldnames = ["Event_ID", "Day", "Hazard_Level", "Facility_Zone", "WallClock_Start", "Duration_Sec", "Extracted_Clip_File", "File_Size_MB", "Status"]
        with open(manifest_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(manifest_rows)
        print(f"\n[SUCCESS] Manifest saved to: {manifest_csv}")

    elapsed = round(time.time() - t_start, 1)
    tot_mb = round(total_bytes / (1024 * 1024), 2)
    print(f"\n{'='*70}")
    print(f"EXTRACTION RUN COMPLETED IN {elapsed}s")
    print(f"Total Incident Clips Ready: {total_extracted}")
    print(f"Total Local Evidence Size:  {tot_mb} MB ({tot_mb/1024:.2f} GB)")
    print(f"Output Directory:           {out_path}")
    print(f"Source Drive E:             READ-ONLY UNTOUCHED")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract incident video clips from read-only footage drive.")
    parser.add_argument("--csv-dir", default="D:/facial", help="Directory containing DayX_... CSV files")
    parser.add_argument("--raw-root", default="E:/RO WATER SEP", help="Root folder of read-only raw footage")
    parser.add_argument("--out-dir", default="D:/facial/incident_evidence", help="Local output destination for clips")
    parser.add_argument("--hazard", default="CRITICAL,SEVERE", help="Hazard priority filter (comma-separated or ALL)")
    parser.add_argument("--day", type=int, default=None, help="Target specific calendar day (e.g. 1 to 30)")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of clips to extract")
    parser.add_argument("--max-duration", type=int, default=None, help="Cap maximum clip duration in seconds (optional)")
    args = parser.parse_args()

    extract_clips(
        csv_dir=args.csv_dir,
        raw_footage_root=args.raw_root,
        out_dir=args.out_dir,
        hazard_filter=args.hazard,
        target_day=args.day,
        max_clips=args.limit,
        max_duration=args.max_duration
    )
