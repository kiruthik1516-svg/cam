"""
Continuous Video Trimmer and Multi-Chunk Demuxer for Engine v2.
"""
from typing import List, Dict, Tuple, Optional
import os
import subprocess
import cv2
import numpy as np
from datetime import datetime, timedelta

from .config import LEAD_IN_BUFFER_SEC, LEAD_OUT_BUFFER_SEC

FFMPEG_EXE = r"C:\Users\mkiru\AppData\Local\Microsoft\WinGet\Links\ffmpeg.exe"
if not os.path.exists(FFMPEG_EXE):
    FFMPEG_EXE = "ffmpeg"

def run_ffmpeg_command(cmd: List[str]) -> Tuple[bool, str]:
    """Executes FFmpeg command safely."""
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=180
        )
        return proc.returncode == 0, proc.stderr
    except Exception as e:
        return False, str(e)

def extract_incident_clip(
    chunk_files: List[Dict[str, any]],
    incident_start_dt: datetime,
    incident_end_dt: datetime,
    output_mp4_path: str,
    lead_in_sec: float = LEAD_IN_BUFFER_SEC,
    lead_out_sec: float = LEAD_OUT_BUFFER_SEC
) -> bool:
    """
    Extracts a seamless video clip covering [incident_start - lead_in, incident_end + lead_out].
    Handles multi-chunk boundaries gracefully.
    chunk_files: list of dicts with keys: {'path': str, 'start_dt': datetime, 'end_dt': datetime}
    """
    os.makedirs(os.path.dirname(output_mp4_path), exist_ok=True)
    target_start = incident_start_dt - timedelta(seconds=lead_in_sec)
    target_end = incident_end_dt + timedelta(seconds=lead_out_sec)
    target_duration = (target_end - target_start).total_seconds()

    # Find overlapping physical files
    overlapping = []
    for cf in chunk_files:
        if cf['start_dt'] < target_end and cf['end_dt'] > target_start:
            overlapping.append(cf)

    if not overlapping:
        return False

    # Case 1: Clip is fully contained within a single file
    if len(overlapping) == 1:
        cf = overlapping[0]
        offset_sec = max(0.0, (target_start - cf['start_dt']).total_seconds())
        cmd = [
            FFMPEG_EXE, "-y",
            "-ss", f"{offset_sec:.3f}",
            "-i", cf['path'],
            "-t", f"{target_duration:.3f}",
            "-c:v", "libx264",
            "-crf", "20",
            "-preset", "ultrafast",
            "-c:a", "aac",
            "-avoid_negative_ts", "make_zero",
            output_mp4_path
        ]
        success, _ = run_ffmpeg_command(cmd)
        return success

    # Case 2: Multi-chunk span across file boundaries
    temp_slices = []
    temp_dir = os.path.dirname(output_mp4_path)
    base_name = os.path.splitext(os.path.basename(output_mp4_path))[0]

    for idx, cf in enumerate(overlapping):
        slice_start = max(target_start, cf['start_dt'])
        slice_end = min(target_end, cf['end_dt'])
        slice_dur = (slice_end - slice_start).total_seconds()
        slice_offset = (slice_start - cf['start_dt']).total_seconds()

        temp_slice_path = os.path.join(temp_dir, f"_temp_{base_name}_part{idx}.mp4")
        temp_slices.append(temp_slice_path)

        cmd = [
            FFMPEG_EXE, "-y",
            "-ss", f"{slice_offset:.3f}",
            "-i", cf['path'],
            "-t", f"{slice_dur:.3f}",
            "-c:v", "libx264",
            "-crf", "20",
            "-preset", "ultrafast",
            "-c:a", "aac",
            "-avoid_negative_ts", "make_zero",
            temp_slice_path
        ]
        success, _ = run_ffmpeg_command(cmd)
        if not success:
            # Clean up and return
            for p in temp_slices:
                if os.path.exists(p): os.remove(p)
            return False

    # Concat the slices
    concat_list_path = os.path.join(temp_dir, f"_concat_{base_name}.txt")
    with open(concat_list_path, "w", encoding="utf-8") as f:
        for p in temp_slices:
            f.write(f"file '{os.path.abspath(p)}'\n")

    cmd = [
        FFMPEG_EXE, "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_list_path,
        "-c", "copy",
        output_mp4_path
    ]
    success, _ = run_ffmpeg_command(cmd)

    # Clean up temporary slice files
    if os.path.exists(concat_list_path): os.remove(concat_list_path)
    for p in temp_slices:
        if os.path.exists(p): os.remove(p)

    return success

