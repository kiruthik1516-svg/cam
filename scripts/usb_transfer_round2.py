"""
USB Pen Drive Transfer Orchestrator - Round 2
Facility: DBGT RO Plant Surveillance Pipeline
Destination: E:\\facial (FAT32 Pen Drive, 28GB Capacity)

Round 2 Scope:
1. Parts 6 through 9 of stage1_candidates.tar (4 parts, ~13.63 GB total).
2. Verifies integrity of all parts via MD5.
3. Outputs reassembly instructions.
"""

import os
import sys
import time
import shutil
import hashlib
from pathlib import Path

SOURCE_ROOT = Path(r"D:\facial")
USB_ROOT = Path(r"E:\facial")
CHUNK_SIZE = 3_500_000_000  # 3.5 GB
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


def main():
    print("=" * 75)
    print(" USB PEN DRIVE TRANSFER - ROUND 2 / 2")
    print(f" Source:      {SOURCE_ROOT}")
    print(f" Destination: {USB_ROOT}")
    print("=" * 75)
    
    if not USB_ROOT.parent.exists():
        print(f"[FATAL] USB Drive root {USB_ROOT.parent} is NOT mounted or available!")
        sys.exit(1)
        
    USB_ROOT.mkdir(parents=True, exist_ok=True)
    t_start = time.time()
    
    master_tar = SOURCE_ROOT / "stage1_candidates.tar"
    if not master_tar.exists():
        print(f"[FATAL] Master dataset {master_tar} was NOT found!")
        sys.exit(1)
        
    master_size = master_tar.stat().st_size
    print(f"\nStreaming Dataset Archive: {master_tar.name} ({format_bytes(master_size)})")
    print("Round 2 Parts to Transfer: Part 6, Part 7, Part 8, Part 9")
    
    checksum_file = USB_ROOT / "checksums_round2.txt"
    checksums = []
    
    with open(master_tar, "rb") as src_f:
        for part_num in range(6, 10):
            part_name = f"stage1_candidates.tar.part{part_num}"
            dst_part = USB_ROOT / part_name
            offset = (part_num - 1) * CHUNK_SIZE
            part_bytes_to_read = min(CHUNK_SIZE, master_size - offset)
            
            print(f"\n  ---> Processing {part_name} ({format_bytes(part_bytes_to_read)})...")
            
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

    # Write reassembly helper scripts
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

    instructions = """===============================================================================
THOORIGAI RO PLANT SURVEILLANCE SYSTEM - ROUND 2 COMPLETE!
===============================================================================

All 9 parts are now transferred across Round 1 and Round 2:
- Round 1: stage1_candidates.tar.part1 to part5 + all code/configs/models
- Round 2: stage1_candidates.tar.part6 to part9

-------------------------------------------------------------------------------
FINAL STEP ON YOUR PC:
-------------------------------------------------------------------------------
1. Copy the 4 files (stage1_candidates.tar.part6, part7, part8, part9) from this
   pen drive into the SAME 'facial' folder on your PC where you pasted Round 1.
2. In that folder, double-click:
      reassemble_stage1.bat
3. The script will automatically merge all 9 parts into the complete 28.99 GB
   'stage1_candidates.tar' archive!
4. Once reassembled, you can delete the .part* files to save 28.99 GB of space!
===============================================================================
"""
    with open(USB_ROOT / "FINAL_REASSEMBLY_INSTRUCTIONS.txt", "w", encoding="utf-8") as f:
        f.write(instructions)
        
    total_el = time.time() - t_start
    print("\n" + "=" * 75)
    print(f" [ROUND 2 COMPLETE] All remaining parts successfully copied in {total_el / 60:.2f} minutes!")
    print(f" Destination Folder: {USB_ROOT}")
    print("=" * 75)
    return 0


if __name__ == "__main__":
    sys.exit(main())

