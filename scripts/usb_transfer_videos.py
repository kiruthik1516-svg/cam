"""
USB Pen Drive Video Transfer Orchestrator
Facility: DBGT RO Plant Surveillance Pipeline
Destination: E:\\facial (FAT32 Pen Drive, 28GB Capacity)

Transfers all extracted incident MP4 video proof clips:
- incident_evidence_v2/ (13.83 GB, 146 MP4 files)
- incident_evidence/ (2.54 GB, MP4 files)
Total Transfer Size: ~16.37 GB (Fits within 28.65 GB free space).
"""

import os
import sys
import time
import shutil
from pathlib import Path

SOURCE_ROOT = Path(r"D:\facial")
USB_ROOT = Path(r"E:\facial")


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
    print(" USB PEN DRIVE TRANSFER - VIDEO EVIDENCE CLIPS")
    print(f" Source:      {SOURCE_ROOT}")
    print(f" Destination: {USB_ROOT}")
    print("=" * 75)
    
    if not USB_ROOT.parent.exists():
        print(f"[FATAL] USB Drive root {USB_ROOT.parent} is NOT mounted or available!")
        sys.exit(1)
        
    USB_ROOT.mkdir(parents=True, exist_ok=True)
    t_start = time.time()
    
    folders_to_copy = ["incident_evidence_v2", "incident_evidence"]
    
    # Calculate total files and bytes
    file_queue = []
    total_bytes = 0
    for folder_name in folders_to_copy:
        src_folder = SOURCE_ROOT / folder_name
        if not src_folder.exists():
            continue
        for root, dirs, files in os.walk(src_folder):
            for f in files:
                if f.lower().endswith(".mp4"):
                    src_p = Path(root) / f
                    rel_p = src_p.relative_to(SOURCE_ROOT)
                    dst_p = USB_ROOT / rel_p
                    sz = src_p.stat().st_size
                    file_queue.append((src_p, dst_p, sz, rel_p))
                    total_bytes += sz
                    
    print(f"Total Video Clips to Copy: {len(file_queue)} files ({format_bytes(total_bytes)})")
    print(f"Available Space on USB:    {format_bytes(shutil.disk_usage(USB_ROOT).free)}")
    print("-" * 75)
    
    copied_bytes = 0
    copied_count = 0
    skipped_count = 0
    
    for idx, (src_p, dst_p, sz, rel_p) in enumerate(file_queue, 1):
        dst_p.parent.mkdir(parents=True, exist_ok=True)
        
        # Check if already copied
        if dst_p.exists() and dst_p.stat().st_size == sz:
            copied_bytes += sz
            skipped_count += 1
            continue
            
        t0 = time.time()
        try:
            shutil.copy2(src_p, dst_p)
            dt = time.time() - t0
            spd = (sz / (1024**2)) / dt if dt > 0 else 0
            copied_bytes += sz
            copied_count += 1
            pct = (copied_bytes / total_bytes) * 100
            print(f"[{idx}/{len(file_queue)}] ({pct:5.1f}%) {rel_p.name} ({format_bytes(sz)}) in {dt:.1f}s ({spd:.1f} MB/s)", flush=True)
        except Exception as e:
            print(f"[ERROR] Failed copying {rel_p}: {e}", flush=True)
            
    total_el = time.time() - t_start
    avg_spd = (copied_bytes / (1024**2)) / total_el if total_el > 0 else 0
    print("\n" + "=" * 75)
    print(f" [COMPLETE] {copied_count} clips copied ({skipped_count} skipped) in {total_el / 60:.2f} minutes!")
    print(f" Total Data Transferred: {format_bytes(copied_bytes)} (Average Speed: {avg_spd:.1f} MB/s)")
    print(f" Destination Folder:     {USB_ROOT}")
    print("=" * 75)
    
    # Write instructions
    note = f"""===============================================================================
THOORIGAI SURVEILLANCE - VIDEO EVIDENCE CLIPS TRANSFER
===============================================================================
Total Videos Transferred: {copied_count} MP4 files ({format_bytes(copied_bytes)})
Includes:
- incident_evidence_v2/ (High-precision 120s incident proof clips, Day 05 & Day 25)
- incident_evidence/ (Baseline forensic proof clips)

INSTRUCTIONS:
Simply copy or move the 'incident_evidence' and 'incident_evidence_v2' folders
from this pen drive into the 'facial' folder on your other PC.
===============================================================================
"""
    with open(USB_ROOT / "VIDEO_CLIPS_INSTRUCTIONS.txt", "w", encoding="utf-8") as f:
        f.write(note)
        
    return 0


if __name__ == "__main__":
    sys.exit(main())

