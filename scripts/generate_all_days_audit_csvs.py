#!/usr/bin/env python3
"""
generate_all_days_audit_csvs.py
Generates:
1. Day{N}_Extracted_Frames_Timestamp_Index.csv
2. Day{N}_Manual_Surveillance_Audit_Sheet.csv
for all days from Day 2 through Day 30 (29 total days).
"""

import csv
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

def format_seconds(seconds: float) -> str:
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

def generate_for_day(day_num: int, master_data: dict, root: Path):
    day_str = f"day_{day_num:02d}"
    cand_dir = root / "data" / "stage1_candidates" / day_str
    manifest_path = cand_dir / "manifest.json"

    if not manifest_path.exists():
        print(f"[WARN] Day {day_num:02d} manifest missing: {manifest_path}")
        return

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    # 1. Collect zone events & personas active on this day
    day_zone_events = []
    day_active_personas = set()
    for p in master_data.get("personas", []):
        pid = p["persona_id"]
        for ev in p.get("zone_events_log", []):
            try:
                dt = datetime.strptime(ev["timestamp"], "%Y-%m-%d %H:%M:%S")
                if dt.day == day_num and dt.month == 9 and dt.year == 2026:
                    day_zone_events.append({
                        "dt": dt,
                        "persona_id": pid,
                        "zone_name": ev.get("zone_name", "Plant Walkway"),
                        "hazard_level": ev.get("hazard_level", "NOMINAL"),
                        "is_direct_contact": ev.get("is_direct_contact", False)
                    })
                    day_active_personas.add(pid)
            except Exception:
                pass

    clips = manifest_data.get("clips", [])
    for c in clips:
        start_dt = parse_clip_start_dt(c["clip"])
        c["start_dt"] = start_dt
        c["end_dt"] = start_dt + timedelta(seconds=c.get("duration_sec", 0))

    clips.sort(key=lambda x: x["start_dt"])

    # Build clip_map for fast candidate indexing
    clip_map = {Path(c["clip"]).stem: c for c in clips}

    # =========================================================================
    # A. Generate Day{N}_Manual_Surveillance_Audit_Sheet.csv
    # =========================================================================
    audit_rows = []
    for idx, c in enumerate(clips, start=1):
        filename = c["clip"]
        start_dt = c["start_dt"]
        end_dt = c["end_dt"]
        dur_sec = c.get("duration_sec", 0)
        ext_frames = c.get("extracted_frames", 0)
        active_sec = c.get("active_window_sec", 0)
        windows = c.get("windows", [])

        if ext_frames > 0:
            status = "ACTIVE (Human Motion Detected)"
        else:
            status = "EMPTY / NOMINAL (0 Motion)"

        # Find matching zone events / personas in this clip's time range
        clip_events = [e for e in day_zone_events if start_dt <= e["dt"] <= end_dt]
        clip_personas = sorted(list({e["persona_id"] for e in clip_events}))

        if clip_events:
            sess_desc_list = []
            for ev in clip_events:
                sess_desc_list.append(f"{ev['persona_id']} @ {ev['dt'].strftime('%H:%M:%S')} [{ev['zone_name']}]")
            sess_str = " | ".join(sess_desc_list[:5])
            if len(sess_desc_list) > 5:
                sess_str += f" (+{len(sess_desc_list)-5} more)"
        elif ext_frames > 0:
            sess_str = "Motion Detected (Unclassified/Transit)"
        else:
            sess_str = "None (No confirmed face session)"

        # Window seek intervals
        if windows:
            seek_windows = []
            clock_windows = []
            for w in windows:
                w_start = w[0]
                w_end = w[1]
                seek_windows.append(f"{format_player_time(w_start)} - {format_player_time(w_end)}")
                w_s_dt = start_dt + timedelta(seconds=w_start)
                w_e_dt = start_dt + timedelta(seconds=w_end)
                clock_windows.append(f"{w_s_dt.strftime('%H:%M:%S')} - {w_e_dt.strftime('%H:%M:%S')}")
            seek_str = ", ".join(seek_windows[:4])
            if len(seek_windows) > 4:
                seek_str += f" (+{len(seek_windows)-4} windows)"
            clock_str = ", ".join(clock_windows[:4])
            if len(clock_windows) > 4:
                clock_str += f" (+{len(clock_windows)-4} intervals)"
        elif ext_frames > 0:
            seek_str = "Activity detected throughout clip"
            clock_str = f"{start_dt.strftime('%H:%M:%S')} - {end_dt.strftime('%H:%M:%S')}"
        else:
            seek_str = "N/A (Clip Empty)"
            clock_str = "N/A (No Activity)"

        # Automated audit notes
        notes = []
        crit_events = [e for e in clip_events if e["hazard_level"] in ("CRITICAL", "SEVERE")]
        if crit_events:
            notes.append(f"CRITICAL: {crit_events[0]['zone_name']} interaction at {crit_events[0]['dt'].strftime('%H:%M:%S')}")
        if start_dt.hour >= 21 or start_dt.hour < 6:
            if ext_frames > 0:
                notes.append("Night Shift Perimeter Patrol")
        notes_str = "; ".join(notes)

        audit_rows.append({
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
            "Automated_Audit_Notes": notes_str,
            "Manual_Human_Present (YES/NO)": "",
            "Manual_Start_Player_Time (MM:SS)": "",
            "Manual_End_Player_Time (MM:SS)": "",
            "Manual_Person_Count": "",
            "Manual_Activity_Observed": "",
            "Equipment_Touched (Valves/Switch/None)": "",
            "Audit_Verdict (MATCH/MISSED/FALSE_ALARM)": "",
            "Reviewer_Comments": "",
        })

    audit_csv = root / f"Day{day_num}_Manual_Surveillance_Audit_Sheet.csv"
    with open(audit_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(audit_rows[0].keys()))
        writer.writeheader()
        writer.writerows(audit_rows)

    # =========================================================================
    # B. Generate Day{N}_Extracted_Frames_Timestamp_Index.csv
    # =========================================================================
    jpgs = sorted(list(cand_dir.glob("*.jpg")))
    frame_rows = []
    prefix = f"day{day_num:02d}_"

    for j in jpgs:
        name = j.name
        parts = name.split("_w")
        if len(parts) != 2:
            continue

        clip_stem = parts[0].replace(prefix, "")
        win_frame = parts[1].split("_")
        win_idx = int(win_frame[0])
        frame_idx = int(win_frame[1].replace(".jpg", ""))

        c_info = clip_map.get(clip_stem)
        if not c_info:
            continue

        start_dt = c_info["start_dt"]
        windows = c_info["windows"]

        if win_idx < len(windows):
            w_start = windows[win_idx][0]
            offset_sec = w_start + (frame_idx - 1)
        else:
            offset_sec = float(frame_idx - 1)

        frame_dt = start_dt + timedelta(seconds=offset_sec)

        # Match persona/session if present
        matching_sess = "None"
        for ev in day_zone_events:
            if abs((ev["dt"] - frame_dt).total_seconds()) <= 15:
                matching_sess = f"{ev['persona_id']} ({ev['zone_name']})"
                break

        frame_rows.append({
            "Frame_File_Name": name,
            "Parent_Video_Clip": c_info["clip"],
            "Clip_Start_Time": start_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "Window_Index": f"w{win_idx:02d}",
            "Frame_Sequence_in_Window": frame_idx,
            "Video_Player_Time_Offset": format_player_time(offset_sec),
            "Calculated_WallClock_Timestamp": frame_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "Operational_Session": matching_sess,
        })

    frame_csv = root / f"Day{day_num}_Extracted_Frames_Timestamp_Index.csv"
    if frame_rows:
        with open(frame_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(frame_rows[0].keys()))
            writer.writeheader()
            writer.writerows(frame_rows)
    else:
        # Create empty template if no frames
        with open(frame_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Frame_File_Name", "Parent_Video_Clip", "Clip_Start_Time",
                "Window_Index", "Frame_Sequence_in_Window", "Video_Player_Time_Offset",
                "Calculated_WallClock_Timestamp", "Operational_Session"
            ])

    print(f"[Day {day_num:02d}] Generated Audit Sheet ({len(audit_rows)} clips) & Frame Index ({len(frame_rows)} frames).")

def main():
    root = Path("D:/facial")
    master_json_path = root / "data" / "30day_personas" / "30day_personas_master.json"

    with open(master_json_path, "r", encoding="utf-8") as f:
        master_data = json.load(f)

    print("Generating Day 2 through Day 30 Audit Sheets and Extracted Frame Indexes...")
    for d in range(2, 31):
        generate_for_day(d, master_data, root)

    print("\n[SUCCESS] Completed generation for all 29 days (Day 2 to Day 30).")

if __name__ == "__main__":
    main()
