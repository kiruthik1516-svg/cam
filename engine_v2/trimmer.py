"""
Continuous Video Trimmer and Multi-Chunk Demuxer for Engine v2.
"""
from typing import List, Dict, Tuple, Optional
import os
import subprocess
import cv2
import numpy as np
from datetime import datetime, timedelta

from pathlib import Path
import shutil

from .config import LEAD_IN_BUFFER_SEC, LEAD_OUT_BUFFER_SEC

REPO_ROOT = Path(__file__).resolve().parent.parent

FFMPEG_EXE = os.getenv("FFMPEG_EXE")
if not FFMPEG_EXE or not shutil.which(FFMPEG_EXE):
    if shutil.which("ffmpeg"):
        FFMPEG_EXE = "ffmpeg"
    elif os.path.exists(r"C:\Users\mkiru\AppData\Local\Microsoft\WinGet\Links\ffmpeg.exe"):
        FFMPEG_EXE = r"C:\Users\mkiru\AppData\Local\Microsoft\WinGet\Links\ffmpeg.exe"
    else:
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

def extract_from_candidate_frames(
    day_num: int,
    target_start: datetime,
    target_end: datetime,
    output_mp4_path: str,
    fps: float = 1.0
) -> bool:
    r"""
    Fallback video synthesizer: When raw physical MP4 chunks on E:\ are unmounted,
    extracts all stage-1 candidate frames for day_num within [target_start, target_end]
    and encodes them into a seamless MP4 evidence video.
    """
    evidence_dir = os.getenv("INCIDENT_EVIDENCE_DIR", str(REPO_ROOT / "incident_evidence"))
    cand_base_dir = os.getenv("STAGE1_CANDIDATES_DIR", str(REPO_ROOT / "data" / "stage1_candidates"))
    idx_path = os.path.join(evidence_dir, f"day_{day_num:02d}", f"Day{day_num}_Extracted_Frames_Timestamp_Index.csv")
    cand_dir = os.path.join(cand_base_dir, f"day_{day_num:02d}")

    if not os.path.exists(idx_path) or not os.path.exists(cand_dir):
        return False

    try:
        import pandas as pd
        df = pd.read_csv(idx_path)
        t_start_str = target_start.strftime("%Y-%m-%d %H:%M:%S")
        t_end_str = target_end.strftime("%Y-%m-%d %H:%M:%S")

        sub = df[(df['Calculated_WallClock_Timestamp'] >= t_start_str) & (df['Calculated_WallClock_Timestamp'] <= t_end_str)]
        
        # If no exact frames in that narrow slice, expand search by 30 seconds
        if len(sub) == 0:
            exp_start = (target_start - timedelta(seconds=30)).strftime("%Y-%m-%d %H:%M:%S")
            exp_end = (target_end + timedelta(seconds=30)).strftime("%Y-%m-%d %H:%M:%S")
            sub = df[(df['Calculated_WallClock_Timestamp'] >= exp_start) & (df['Calculated_WallClock_Timestamp'] <= exp_end)]

        valid_files = []
        for _, r in sub.iterrows():
            fpath = os.path.join(cand_dir, r['Frame_File_Name'])
            if os.path.exists(fpath):
                valid_files.append(fpath)

        if not valid_files:
            return False

        temp_dir = os.path.dirname(output_mp4_path)
        base_name = os.path.splitext(os.path.basename(output_mp4_path))[0]
        concat_list_path = os.path.join(temp_dir, f"_concat_fallback_{base_name}.txt")

        with open(concat_list_path, "w", encoding="utf-8") as f:
            for vf in valid_files:
                clean_p = vf.replace("\\", "/")
                f.write(f"file '{clean_p}'\n")
                f.write(f"duration {1.0 / fps:.3f}\n")
            f.write(f"file '{valid_files[-1].replace('\\', '/')}'\n")

        cmd = [
            FFMPEG_EXE, "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_list_path,
            "-c:v", "libx264",
            "-crf", "20",
            "-preset", "ultrafast",
            "-pix_fmt", "yuv420p",
            output_mp4_path
        ]
        success, _ = run_ffmpeg_command(cmd)

        if os.path.exists(concat_list_path):
            os.remove(concat_list_path)

        return success
    except Exception as e:
        return False

def extract_incident_clip(
    chunk_files: List[Dict[str, any]],
    incident_start_dt: datetime,
    incident_end_dt: datetime,
    output_mp4_path: str,
    lead_in_sec: float = LEAD_IN_BUFFER_SEC,
    lead_out_sec: float = LEAD_OUT_BUFFER_SEC,
    day_num: Optional[int] = None
) -> bool:
    """
    Extracts a seamless video clip covering [incident_start - lead_in, incident_end + lead_out].
    Handles multi-chunk boundaries gracefully.
    Falls back to stage-1 candidate frame synthesis when raw physical storage is unmounted.
    """
    os.makedirs(os.path.dirname(output_mp4_path), exist_ok=True)
    target_start = incident_start_dt - timedelta(seconds=lead_in_sec)
    target_end = incident_end_dt + timedelta(seconds=lead_out_sec)
    target_duration = (target_end - target_start).total_seconds()

    d_num = day_num if day_num is not None else incident_start_dt.day

    # Find overlapping physical files that exist on disk
    overlapping = []
    if chunk_files:
        for cf in chunk_files:
            if cf['start_dt'] < target_end and cf['end_dt'] > target_start:
                if os.path.exists(cf['path']):
                    overlapping.append(cf)

    # Physical drive unmounted / offline fallback
    if not overlapping:
        return extract_from_candidate_frames(d_num, target_start, target_end, output_mp4_path)

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

