#!/usr/bin/env python3
"""
organize_incident_evidence.py
Organizes D:\\facial\\incident_evidence into dedicated day folders (day_01 to day_30).
Also copies the day's audit CSVs into each folder for an all-in-one standalone daily forensic dossier.
Updates extracted_incident_manifest.csv with relative paths.
"""

import csv
import glob
import os
from pathlib import Path
import re
import shutil

def organize():
    root = Path("D:/facial")
    evidence_dir = root / "incident_evidence"

    if not evidence_dir.exists():
        print(f"[ERROR] Evidence directory not found: {evidence_dir}")
        return

    # 1. Ensure all 30 day folders exist
    for d in range(1, 31):
        day_folder = evidence_dir / f"day_{d:02d}"
        day_folder.mkdir(parents=True, exist_ok=True)

    # 2. Move video and verification files into their respective day folders
    all_files = [f for f in evidence_dir.iterdir() if f.is_file() and f.name != "extracted_incident_manifest.csv"]
    moved_count = 0

    for f in all_files:
        day_num = None
        # Match Day01, Day1, Day_01, etc.
        m = re.search(r'Day_?(\d+)', f.name, re.IGNORECASE)
        if m:
            day_num = int(m.group(1))
        elif "D01" in f.name or "095338" in f.name or "222736" in f.name:
            day_num = 1
        elif "d15" in f.name.lower():
            day_num = 15

        if day_num and 1 <= day_num <= 30:
            target_dir = evidence_dir / f"day_{day_num:02d}"
            target_path = target_dir / f.name
            shutil.move(str(f), str(target_path))
            moved_count += 1

    print(f"[OK] Organized {moved_count} video/media files into day_01 through day_30 folders.")

    # 3. Copy corresponding daily CSV audit sheets into each day folder for all-in-one standalone review
    csv_copied = 0
    for d in range(1, 31):
        day_target = evidence_dir / f"day_{d:02d}"

        # Clipping index
        clip_csv = root / f"Day{d}_Persona_Video_Clipping_Index.csv"
        if clip_csv.exists():
            shutil.copy2(str(clip_csv), str(day_target / clip_csv.name))
            csv_copied += 1

        # Audit sheet
        audit_csv = root / f"Day{d}_Manual_Surveillance_Audit_Sheet.csv"
        if audit_csv.exists():
            shutil.copy2(str(audit_csv), str(day_target / audit_csv.name))
            csv_copied += 1

        # Frame index
        frame_csv = root / f"Day{d}_Extracted_Frames_Timestamp_Index.csv"
        if frame_csv.exists():
            shutil.copy2(str(frame_csv), str(day_target / frame_csv.name))
            csv_copied += 1

    print(f"[OK] Copied {csv_copied} daily audit CSVs into day folders for standalone review.")

    # 4. Update extracted_incident_manifest.csv with relative paths
    manifest_path = evidence_dir / "extracted_incident_manifest.csv"
    if manifest_path.exists():
        with open(manifest_path, "r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))

        updated_rows = []
        for r in reader:
            d_num = int(r.get("Day", 1))
            fname = Path(r["Extracted_Clip_File"]).name
            r["Extracted_Clip_File"] = f"day_{d_num:02d}/{fname}"
            updated_rows.append(r)

        with open(manifest_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(updated_rows[0].keys()))
            writer.writeheader()
            writer.writerows(updated_rows)

        print(f"[OK] Updated manifest with relative paths ({len(updated_rows)} records).")

    # 5. Print overview
    print("\n=== Incident Evidence Organization Summary ===")
    for d in range(1, 31):
        day_folder = evidence_dir / f"day_{d:02d}"
        mp4s = list(day_folder.glob("*.mp4"))
        csvs = list(day_folder.glob("*.csv"))
        total_mb = sum(f.stat().st_size for f in mp4s) / (1024 * 1024)
        print(f"  day_{d:02d}/: {len(mp4s):2d} MP4 video clips ({total_mb:6.1f} MB), {len(csvs)} audit CSVs")

if __name__ == "__main__":
    organize()

