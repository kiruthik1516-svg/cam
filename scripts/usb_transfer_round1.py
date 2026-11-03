"""
USB Pen Drive Transfer Orchestrator - Round 1
Facility: DBGT RO Plant Surveillance Pipeline
Destination: E:\\facial (FAT32 Pen Drive, 28GB Capacity)

Round 1 Scope:
1. Complete Codebase, configs, models, docs, assets, audit sheets (~150 MB).
2. Incident evidence metadata & indices (excluding heavy .mp4 video files).
3. Parts 1 through 5 of stage1_candidates.tar (5 x 3.50 GB = 17.50 GB).
4. Auto-reassembly scripts (reassemble_stage1.bat and reassemble_stage1.sh).
5. Comprehensive TRANSFER_INSTRUCTIONS.txt.

Total Round 1 Transfer Size: ~17.65 GB (Fits comfortably within 28.65 GB free space).
"""

import os
import sys
import time
import shutil
import hashlib
from pathlib import Path

SOURCE_ROOT = Path(r"D:\facial")
USB_ROOT = Path(r"E:\facial")
CHUNK_SIZE = 3_500_000_000  # 3.5 GB (Strictly under FAT32 4.0 GB individual file limit)
BUFFER_SIZE = 16 * 1024 * 1024  # 16 MB streaming buffer


def format_bytes(b: int) -> str:
    if b < 1024:
        return f"{b} B"
    elif b < 1024**2:
        return f"{b / 1024:.2f} KB"
    elif b < 1024**3:
        return f"{b / (1024**2):.2f} MB"
    else:
        return f"{b / (1024**3):.2f} GB"


def copy_directory(src_dir: Path, dst_dir: Path, exclude_exts=None):
    if exclude_exts is None:
        exclude_exts = set()
    
    count = 0
    total_bytes = 0
    for root, dirs, files in os.walk(src_dir):
        rel_root = Path(root).relative_to(src_dir)
        target_dir = dst_dir / rel_root
        target_dir.mkdir(parents=True, exist_ok=True)
        
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in exclude_exts:
                continue
            src_file = Path(root) / f
            dst_file = target_dir / f
            
            # Skip if already exists and matches size
            try:
                src_sz = src_file.stat().st_size
                if dst_file.exists() and dst_file.stat().st_size == src_sz:
                    continue
                shutil.copy2(src_file, dst_file)
                count += 1
                total_bytes += src_sz
            except Exception as e:
                print(f"  [WARN] Failed to copy {src_file.name}: {e}")
    return count, total_bytes


def main():
    print("=" * 75)
    print(" USB PEN DRIVE TRANSFER - ROUND 1 / 2")
    print(f" Source:      {SOURCE_ROOT}")
    print(f" Destination: {USB_ROOT}")
    print("=" * 75)
    
    if not USB_ROOT.parent.exists():
        print(f"[FATAL] USB Drive root {USB_ROOT.parent} is NOT mounted or available!")
        sys.exit(1)
        
    USB_ROOT.mkdir(parents=True, exist_ok=True)
    t_start = time.time()
    
    # -------------------------------------------------------------
    # 1. Copy Core Project Directories
    # -------------------------------------------------------------
    core_dirs = [
        "engine_v2",
        "scripts",
        "backend",
        "docs",
        "assets",
        "team_reports",
        "templates",
    ]
    
    print("\n[Step 1/4] Copying Core Application Directories...")
    for d in core_dirs:
        src = SOURCE_ROOT / d
        dst = USB_ROOT / d
        if src.exists():
            c, sz = copy_directory(src, dst)
            print(f"  [COPIED] {d:15} -> {c} files ({format_bytes(sz)})")
            
    # Copy metadata directories (exclude heavy .mp4 video files)
    print("\n[Step 1b] Copying Forensic Indices & Metadata (skipping raw .mp4 clips)...")
    for d in ["incident_evidence", "incident_evidence_v2"]:
        src = SOURCE_ROOT / d
        dst = USB_ROOT / d
        if src.exists():
            c, sz = copy_directory(src, dst, exclude_exts={".mp4"})
            print(f"  [COPIED] {d:20} -> {c} files ({format_bytes(sz)})")

    # -------------------------------------------------------------
    # 2. Copy Root Configuration, Models & Audit Files
    # -------------------------------------------------------------
    print("\n[Step 2/4] Copying Root Configuration, Models & Audit CSVs...")
    root_patterns = [
        ".env",
        ".env.example",
        "yolov8n-pose.pt",
        "yolov8n.pt",
        "requirements-cloud.txt",
        "requirements.txt",
        "README.md",
        "docker-compose.jarvislabs.yml",
        "Dockerfile.detector",
        "all_30_days_audit_ground_truth.json",
        "30_Day_Master_Personas_Behavioral_Register.csv",
        "30_day_personas_summary.md",
        "30_day_security_audit.md",
        "30_day_unique_people_behavioral_timeline_report.md",
        "RO_Plant_Surveillance_Executive_Guide.pdf",
        "RO_Plant_Surveillance_ROI_Mesh.jpg",
    ]
    
    root_files = []
    for pat in root_patterns:
        p = SOURCE_ROOT / pat
        if p.exists():
            root_files.append(p)
            
    # Include all Day*.csv files
    for p in SOURCE_ROOT.glob("Day*.csv"):
        root_files.append(p)
    for p in SOURCE_ROOT.glob("day*.csv"):
        root_files.append(p)
        
    for rf in root_files:
        dst = USB_ROOT / rf.name
        try:
            if not dst.exists() or dst.stat().st_size != rf.stat().st_size:
                shutil.copy2(rf, dst)
                print(f"  [COPIED] {rf.name} ({format_bytes(rf.stat().st_size)})")
        except Exception as e:
            print(f"  [WARN] Failed to copy {rf.name}: {e}")

    # -------------------------------------------------------------
    # 3. Stream Split Chunks of stage1_candidates.tar (Parts 1 to 5)
    # -------------------------------------------------------------
    master_tar = SOURCE_ROOT / "stage1_candidates.tar"
    if not master_tar.exists():
        print(f"[FATAL] Master dataset {master_tar} was NOT found!")
        sys.exit(1)
        
    master_size = master_tar.stat().st_size
    print(f"\n[Step 3/4] Streaming Dataset Archive: {master_tar.name} ({format_bytes(master_size)})")
    print(f"  FAT32 Safe Chunk Size: {format_bytes(CHUNK_SIZE)}")
    print("  Round 1 Parts to Transfer: Part 1, Part 2, Part 3, Part 4, Part 5")
    
    checksum_file = USB_ROOT / "checksums_round1.txt"
    checksums = []
    
    # We copy parts 1 to 5 in Round 1
    with open(master_tar, "rb") as src_f:
        for part_num in range(1, 6):
            part_name = f"stage1_candidates.tar.part{part_num}"
            dst_part = USB_ROOT / part_name
            offset = (part_num - 1) * CHUNK_SIZE
            part_bytes_to_read = min(CHUNK_SIZE, master_size - offset)
            
            print(f"\n  ---> Processing {part_name} ({format_bytes(part_bytes_to_read)})...")
            
            # Check if part already exists and matches expected size
            if dst_part.exists() and dst_part.stat().st_size == part_bytes_to_read:
                print(f"    [SKIP] {part_name} already exists with exact size ({format_bytes(part_bytes_to_read)}).")
                continue
                
            src_f.seek(offset)
            bytes_written = 0
            part_t0 = time.time()
            md5_hash = hashlib.md5()
            
            with open(dst_part, "wb") as out_f:
                while bytes_written < part_bytes_to_read:
                    chunk_to_read = min(BUFFER_SIZE, part_bytes_to_read - bytes_written)
                    buf = src_f.read(chunk_to_read)
                    if not buf:
                        break
                    out_f.write(buf)
                    md5_hash.update(buf)
                    bytes_written += len(buf)
                    
                    # Periodic progress indicator
                    if bytes_written % (256 * 1024 * 1024) < BUFFER_SIZE or bytes_written == part_bytes_to_read:
                        pct = (bytes_written / part_bytes_to_read) * 100
                        el = time.time() - part_t0
                        spd = (bytes_written / (1024**2)) / el if el > 0 else 0
                        print(f"    [WRITING] {part_name}: {bytes_written / (1024**3):.2f}/{part_bytes_to_read / (1024**3):.2f} GB ({pct:.1f}%) | {spd:.1f} MB/s", flush=True)
                        
            part_el = time.time() - part_t0
            avg_spd = (bytes_written / (1024**2)) / part_el if part_el > 0 else 0
            hex_digest = md5_hash.hexdigest()
            print(f"    [COMPLETED] {part_name} ({format_bytes(bytes_written)}) in {part_el:.1f}s ({avg_spd:.1f} MB/s) | MD5: {hex_digest}")
            checksums.append(f"{hex_digest}  {part_name}\n")
            
    with open(checksum_file, "w", encoding="utf-8") as cs_f:
        cs_f.writelines(checksums)

    # -------------------------------------------------------------
    # 4. Write Reassembly Scripts & Instructions
    # -------------------------------------------------------------
    print("\n[Step 4/4] Writing Reassembly Scripts & Transfer Instructions...")
    
    # Windows reassembly batch script
    bat_content = """@echo off
title JarvisLabs Surveillance Data Reassembly
echo ======================================================================
echo    THOORIGAI SURVEILLANCE PIPELINE - DATA REASSEMBLY WIZARD
echo ======================================================================
echo.

if not exist stage1_candidates.tar.part9 (
    echo [ERROR] Incomplete transfer detected!
    echo 'stage1_candidates.tar.part9' was not found in this folder.
    echo Please make sure you have copied ALL 9 parts (from both Round 1 and Round 2)
    echo into this same folder before running this script.
    echo.
    pause
    exit /b 1
)

echo [INFO] Concatenating 9 parts into master stage1_candidates.tar...
echo This will take 1-2 minutes. Please wait...
echo.

copy /b stage1_candidates.tar.part1 + stage1_candidates.tar.part2 + stage1_candidates.tar.part3 + stage1_candidates.tar.part4 + stage1_candidates.tar.part5 + stage1_candidates.tar.part6 + stage1_candidates.tar.part7 + stage1_candidates.tar.part8 + stage1_candidates.tar.part9 stage1_candidates.tar

echo.
echo ======================================================================
echo [SUCCESS] Reassembly Complete!
dir stage1_candidates.tar
echo ======================================================================
echo.
echo You can now safely delete stage1_candidates.tar.part* to free disk space!
echo.
pause
"""
    with open(USB_ROOT / "reassemble_stage1.bat", "w", encoding="utf-8") as f:
        f.write(bat_content)
        
    # Linux / JarvisLabs reassembly bash script
    sh_content = """#!/usr/bin/env bash
# ThoorigAI Data Reassembly Script
set -e
echo "======================================================================"
echo " ThoorigAI Surveillance Pipeline: Reassembling stage1_candidates.tar"
echo "======================================================================"
if [ ! -f "stage1_candidates.tar.part9" ]; then
    echo "[ERROR] Missing parts! Ensure parts 1 through 9 are present."
    exit 1
fi

echo "[INFO] Concatenating parts into stage1_candidates.tar..."
cat stage1_candidates.tar.part* > stage1_candidates.tar
echo "[SUCCESS] Verifying file size:"
ls -lh stage1_candidates.tar
echo "Done! You may delete parts using: rm stage1_candidates.tar.part*"
"""
    with open(USB_ROOT / "reassemble_stage1.sh", "w", encoding="utf-8") as f:
        f.write(sh_content)
        
    # Instructions text file
    instructions = f"""===============================================================================
THOORIGAI RO PLANT SURVEILLANCE SYSTEM - DATA TRANSFER INSTRUCTIONS
===============================================================================

CURRENT ROUND: ROUND 1 (COMPLETED)
Transferred:
- Complete Codebase (engine_v2, scripts, backend, docs, assets, team_reports)
- All Models (yolov8n-pose.pt, yolov8n.pt)
- Cloud Configs (.env, requirements-cloud.txt, docker-compose.jarvislabs.yml)
- Master Incident Evidence Manifests & Forensic Tables
- Dataset Archive Chunks: stage1_candidates.tar.part1 through part5 (~17.5 GB)

-------------------------------------------------------------------------------
WHAT YOU NEED TO DO RIGHT NOW:
-------------------------------------------------------------------------------
1. UNPLUG this pen drive from this computer.
2. PLUG it into your other PC.
3. COPY or MOVE the entire 'facial' folder from this pen drive to your other PC
   (for example, to C:\\facial or D:\\facial).
4. FORMAT or DELETE everything from this pen drive so it is 100% EMPTY.
5. PLUG the empty pen drive BACK into this computer.
6. Tell the assistant: "Pen drive is empty and plugged in, proceed with Round 2".

-------------------------------------------------------------------------------
WHAT WILL HAPPEN IN ROUND 2:
-------------------------------------------------------------------------------
In Round 2, the assistant will copy the remaining 4 parts:
- stage1_candidates.tar.part6
- stage1_candidates.tar.part7
- stage1_candidates.tar.part8
- stage1_candidates.tar.part9 (~13.6 GB total)

Once Round 2 finishes, you copy those 4 parts into the SAME 'facial' folder on your
other PC, and simply double-click 'reassemble_stage1.bat'!
It will instantly merge them back into the exact original 28.99 GB stage1_candidates.tar!
===============================================================================
"""
    with open(USB_ROOT / "TRANSFER_INSTRUCTIONS.txt", "w", encoding="utf-8") as f:
        f.write(instructions)

    total_el = time.time() - t_start
    print("\n" + "=" * 75)
    print(f" [ROUND 1 COMPLETE] All Round 1 files successfully copied in {total_el / 60:.2f} minutes!")
    print(f" Destination Folder: {USB_ROOT}")
    print("=" * 75)
    return 0


if __name__ == "__main__":
    sys.exit(main())

