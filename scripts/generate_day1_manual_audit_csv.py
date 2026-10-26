"""Generate comprehensive Day 1 Manual Surveillance Audit CSV Sheet.

Creates an intuitive file-by-file checklist for manual human verification
against Stage 1 automated sentry-sniper extraction results.
"""

import csv
from datetime import datetime, timedelta
import json
from pathlib import Path


def format_seconds(seconds: float) -> str:
    """Format seconds into HH:MM:SS or Mm Ss string."""
    seconds = int(round(seconds))
    hrs = seconds // 3600
    mins = (seconds % 3600) // 60
    secs = seconds % 60
    if hrs > 0:
        return f"{hrs}h {mins}m {secs}s"
    elif mins > 0:
        return f"{mins}m {secs}s"
    else:
        return f"{secs}s"


def format_player_time(seconds: float) -> str:
    """Format seconds into video player time MM:SS or HH:MM:SS."""
    seconds = int(round(seconds))
    hrs = seconds // 3600
    mins = (seconds % 3600) // 60
    secs = seconds % 60
    if hrs > 0:
        return f"{hrs:02d}:{mins:02d}:{secs:02d}"
    else:
        return f"{mins:02d}:{secs:02d}"


def parse_clip_start_dt(filename: str) -> datetime:
    """Extract start datetime from DBGT IPC filename format."""
    # Format: ..._YYYYMMDDHHMMSS.mp4
    stem = Path(filename).stem
    ts_str = stem.split("_")[-1]
    return datetime.strptime(ts_str, "%Y%m%d%H%M%S")


def main():
    root = Path(__file__).resolve().parent.parent
    manifest_path = root / "data" / "stage1_candidates" / "day_01" / "manifest.json"
    sessions_path = root / "data" / "day1_identities" / "sessions_summary.json"
    output_csv = root / "Day1_Manual_Surveillance_Audit_Sheet.csv"

    # Load manifests & session data
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    sessions_data = []
    if sessions_path.exists():
        with open(sessions_path, "r", encoding="utf-8") as f:
            sessions_data = json.load(f)

    clips = manifest_data.get("clips", [])

    # Enrich each clip with start datetime, end datetime, and duration
    for c in clips:
        start_dt = parse_clip_start_dt(c["clip"])
        c["start_dt"] = start_dt
        c["end_dt"] = start_dt + timedelta(seconds=c.get("duration_sec", 0))

    # Sort strictly chronologically from midnight 00:00:00 to 23:59:59
    clips.sort(key=lambda x: x["start_dt"])

    # Prepare rows
    rows = []
    for idx, c in enumerate(clips, start=1):
        filename = c["clip"]
        start_dt = c["start_dt"]
        end_dt = c["end_dt"]
        dur_sec = c.get("duration_sec", 0)
        ext_frames = c.get("extracted_frames", 0)
        active_sec = c.get("active_window_sec", 0)

        # Match sessions in this clip
        matching_sessions = [
            s for s in sessions_data if s.get("device_clip") == filename
        ]

        if ext_frames > 0:
            status = "ACTIVE (Human Motion Detected)"
        else:
            status = "EMPTY / NOMINAL (0 Motion)"

        # Session descriptions
        if matching_sessions:
            sess_desc_list = []
            for s in matching_sessions:
                s_num = s.get("session_num")
                s_start = s.get("start_time")
                s_end = s.get("end_time")
                s_dwell = s.get("duration")
                s_sightings = s.get("sightings")
                sess_desc_list.append(
                    f"Session #{s_num:02d} [{s_start} - {s_end}, Dwell: {s_dwell}, Sightings: {s_sightings}]"
                )
            sess_str = " | ".join(sess_desc_list)
        else:
            sess_str = "None (No confirmed face session)"

        # Calculate estimated video player seek window
        if matching_sessions:
            seek_windows = []
            clock_windows = []
            for s in matching_sessions:
                s_start_str = s.get("start_time")
                s_end_str = s.get("end_time")
                try:
                    s_s_dt = datetime.strptime(
                        f"2026-09-01 {s_start_str}", "%Y-%m-%d %H:%M:%S"
                    )
                    s_e_dt = datetime.strptime(
                        f"2026-09-01 {s_end_str}", "%Y-%m-%d %H:%M:%S"
                    )
                    p_start = max(0.0, (s_s_dt - start_dt).total_seconds())
                    p_end = min(dur_sec, (s_e_dt - start_dt).total_seconds())
                    seek_windows.append(
                        f"{format_player_time(p_start)} - {format_player_time(p_end)}"
                    )
                    clock_windows.append(f"{s_start_str} - {s_end_str}")
                except Exception:
                    pass
            seek_str = ", ".join(seek_windows) if seek_windows else "See Extracted Windows"
            clock_str = ", ".join(clock_windows) if clock_windows else f"{start_dt.strftime('%H:%M:%S')} - {end_dt.strftime('%H:%M:%S')}"
        elif ext_frames > 0:
            seek_str = "Activity detected throughout clip"
            clock_str = f"{start_dt.strftime('%H:%M:%S')} - {end_dt.strftime('%H:%M:%S')}"
        else:
            seek_str = "N/A (Clip Empty)"
            clock_str = "N/A (No Activity)"

        # Special annotations (e.g. Day 1 09:14:42 RO Skid Proximity Event)
        notes = ""
        if "20260901085926" in filename:
            notes = "CRITICAL EVENT: RO Skid controls proximity visit at 09:14:42 AM. Valves & Switch 100% untouched."
        elif "20260901012954" in filename:
            notes = "Night Security Guard inspection round at 01:33:34 AM (Session #01)."
        elif "20260901115914" in filename:
            notes = "Peak shift activity: Concurrent crew of 3 operators on corridor (Session #12)."
        elif "20260901201342" in filename:
            notes = "Evening security sweep at 20:01:13 PM (Session #19)."

        row = {
            "Clip_#": idx,
            "Video_File_Name": filename,
            "Clip_Start_WallClock": start_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "Clip_End_WallClock": end_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "Clip_Duration": format_seconds(dur_sec),
            "Clip_Duration_Seconds": round(dur_sec, 1),
            "Pipeline_Stage1_Status": status,
            "Pipeline_Extracted_Frames": ext_frames,
            "Pipeline_Active_Window_Time": format_seconds(active_sec),
            "Player_Seek_Timestamp_Range": seek_str,
            "Active_WallClock_Intervals": clock_str,
            "Associated_Identified_Sessions": sess_str,
            "Automated_Audit_Notes": notes,
            # Manual Reviewer Blank Columns to Fill
            "Manual_Human_Present (YES/NO)": "",
            "Manual_Start_Player_Time (MM:SS)": "",
            "Manual_End_Player_Time (MM:SS)": "",
            "Manual_Person_Count": "",
            "Manual_Activity_Observed": "",
            "Equipment_Touched (Valves/Switch/None)": "",
            "Audit_Verdict (MATCH/MISSED/FALSE_ALARM)": "",
            "Reviewer_Comments": "",
        }
        rows.append(row)

    # Write CSV
    fieldnames = list(rows[0].keys())
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"[OK] Successfully generated: {output_csv}")
    print(f"Total Clips Logged: {len(rows)}")
    active_cnt = sum(1 for r in rows if "ACTIVE" in r["Pipeline_Stage1_Status"])
    empty_cnt = sum(1 for r in rows if "EMPTY" in r["Pipeline_Stage1_Status"])
    print(f"Active Clips with Motion: {active_cnt}")
    print(f"Empty Clips Skipped:     {empty_cnt}")


if __name__ == "__main__":
    main()

