"""Generate Image-Level Timestamp Index for Day 1 Extracted Candidate Crops.

Maps all 6,400 candidate JPEG crops in data/stage1_candidates/day_01/
to their parent video clip, window index, estimated video player offset,
and wall-clock timestamp.
"""

import csv
from datetime import datetime, timedelta
import json
from pathlib import Path


def format_player_time(seconds: float) -> str:
    seconds = int(round(seconds))
    hrs = seconds // 3600
    mins = (seconds % 3600) // 60
    secs = seconds % 60
    if hrs > 0:
        return f"{hrs:02d}:{mins:02d}:{secs:02d}"
    else:
        return f"{mins:02d}:{secs:02d}"


def parse_clip_start_dt(filename: str) -> datetime:
    stem = Path(filename).stem
    ts_str = stem.split("_")[-1]
    return datetime.strptime(ts_str, "%Y%m%d%H%M%S")


def main():
    root = Path(__file__).resolve().parent.parent
    day1_dir = root / "data" / "stage1_candidates" / "day_01"
    manifest_path = day1_dir / "manifest.json"
    sessions_path = root / "data" / "day1_identities" / "sessions_summary.json"
    output_csv = root / "Day1_Extracted_Frames_Timestamp_Index.csv"

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    sessions_data = []
    if sessions_path.exists():
        with open(sessions_path, "r", encoding="utf-8") as f:
            sessions_data = json.load(f)

    # Build clip lookup: stem -> clip metadata
    clip_map = {}
    for c in manifest_data.get("clips", []):
        clip_name = c["clip"]
        stem = Path(clip_name).stem
        start_dt = parse_clip_start_dt(clip_name)
        clip_map[stem] = {
            "filename": clip_name,
            "start_dt": start_dt,
            "duration_sec": c.get("duration_sec", 0),
            "windows": c.get("windows", []),
        }

    jpgs = sorted(list(day1_dir.glob("*.jpg")))
    print(f"Indexing {len(jpgs)} extracted candidate frames...")

    rows = []
    for j in jpgs:
        name = j.name
        # format: day01_<clip_stem>_w<win_idx>_<frame_idx>.jpg
        parts = name.split("_w")
        if len(parts) != 2:
            continue

        clip_stem = parts[0].replace("day01_", "")
        win_frame = parts[1].split("_")
        win_idx = int(win_frame[0])
        frame_idx = int(win_frame[1].replace(".jpg", ""))

        c_info = clip_map.get(clip_stem)
        if not c_info:
            continue

        start_dt = c_info["start_dt"]
        windows = c_info["windows"]

        # Calculate offset in seconds
        if win_idx < len(windows):
            w_start = windows[win_idx][0]
            offset_sec = w_start + (frame_idx - 1)
        else:
            # Fallback estimation based on frame index
            offset_sec = float(frame_idx - 1)

        frame_dt = start_dt + timedelta(seconds=offset_sec)
        time_str = frame_dt.strftime("%H:%M:%S")

        # Match session if applicable
        matching_sess = "None"
        for s in sessions_data:
            if s.get("device_clip") == c_info["filename"]:
                s_start = s.get("start_time")
                s_end = s.get("end_time")
                if s_start <= time_str <= s_end:
                    matching_sess = f"Session #{s.get('session_num'):02d} ({s.get('duration')})"
                    break

        rows.append({
            "Frame_File_Name": name,
            "Parent_Video_Clip": c_info["filename"],
            "Clip_Start_Time": start_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "Window_Index": f"w{win_idx:02d}",
            "Frame_Sequence_in_Window": frame_idx,
            "Video_Player_Time_Offset": format_player_time(offset_sec),
            "Calculated_WallClock_Timestamp": frame_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "Operational_Session": matching_sess,
        })

    fieldnames = list(rows[0].keys())
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"[OK] Successfully wrote {len(rows)} frame records to: {output_csv}")


if __name__ == "__main__":
    main()

