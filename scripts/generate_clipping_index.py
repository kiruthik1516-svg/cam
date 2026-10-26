"""Generate Video Clipping Timeframe Index for later physical disk extraction.

When the user connects their raw footage hard drive later, this index provides
exact start/end timestamps, clip offsets (MM:SS), zone interaction tags, and
ready-to-run FFmpeg commands so all incident clips can be extracted with zero re-indexing.
"""

import argparse
import csv
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
from sqlalchemy import create_engine, text

CRITICAL_ZONES = {
    "multiport_valves": {
        "name": "Two Multiport Backwash Valves",
        "bbox": [755, 220, 985, 360],
        "hazard_level": "CRITICAL",
    },
    "ultimate_power_switch": {
        "name": "Ultimate Plant Power Switch",
        "bbox": [998, 155, 1090, 265],
        "hazard_level": "SEVERE",
    },
    "ro_skid_controls": {
        "name": "RO Skid Controls & Walkway",
        "bbox": [945, 345, 1210, 510],
        "hazard_level": "ELEVATED",
    },
}


def check_zone(bbox):
    for zid, zdata in CRITICAL_ZONES.items():
        zb = zdata["bbox"]
        xA, yA = max(bbox[0], zb[0]), max(bbox[1], zb[1])
        xB, yB = min(bbox[2], zb[2]), min(bbox[3], zb[3])
        if xB > xA and yB > yA:
            return zdata["name"], zdata["hazard_level"]
        cx, cy = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
        margin = 40
        if (zb[0] - margin <= cx <= zb[2] + margin) and (zb[1] - margin <= cy <= zb[3] + margin):
            return f"{zdata['name']} (Proximity)", zdata["hazard_level"]
    return "Plant Walkway / General Area", "NOMINAL"


def format_mmss(seconds):
    m = int(seconds) // 60
    s = int(seconds) % 60
    h = m // 60
    m = m % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def generate_clipping_csv(db_url, output_csv="Day1_Persona_Video_Clipping_Index.csv", camera_id="IPC56", batch_id=None, day_num=1):
    engine = create_engine(db_url)
    where_clauses = ["camera_id = :cam_id", "embedding_vector IS NOT NULL"]
    params = {"cam_id": camera_id}

    if batch_id:
        where_clauses.append("batch_id = :batch_id")
        params["batch_id"] = batch_id

    where_sql = " AND ".join(where_clauses)

    with engine.connect() as conn:
        rows = conn.execute(text(f"""
            SELECT id, batch_id, camera_id, timestamp, sequence_number,
                   bbox, quality_score, device_id
            FROM detections
            WHERE {where_sql}
            ORDER BY device_id, sequence_number ASC
        """), params).fetchall()

    if not rows:
        print("No detections found to generate clipping index.")
        return

    events = []
    current_event = None

    for r in rows:
        det_id, b_id, cam_id, ts, seq_sec, bbox_raw, q_score, clip_file = r
        bbox = json.loads(bbox_raw) if isinstance(bbox_raw, str) else bbox_raw
        zone_name, hazard = check_zone(bbox)

        if current_event is None or current_event["clip_file"] != clip_file or (seq_sec - current_event["end_sec"]) > 15:
            if current_event is not None:
                events.append(current_event)
            current_event = {
                "clip_file": clip_file,
                "start_ts": ts,
                "end_ts": ts,
                "start_sec": max(0, seq_sec - 5),
                "end_sec": seq_sec + 5,
                "zone_name": zone_name,
                "hazard": hazard,
                "max_quality": q_score,
                "detection_count": 1,
            }
        else:
            current_event["end_ts"] = ts
            current_event["end_sec"] = seq_sec + 5
            current_event["detection_count"] += 1
            if q_score and (current_event["max_quality"] is None or q_score > current_event["max_quality"]):
                current_event["max_quality"] = q_score
            if hazard != "NOMINAL":
                current_event["zone_name"] = zone_name
                current_event["hazard"] = hazard

    if current_event is not None:
        events.append(current_event)

    Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Event_ID",
            "Clip_Filename",
            "Start_WallClock_Time",
            "End_WallClock_Time",
            "Seek_Start_Offset",
            "Seek_End_Offset",
            "Duration_Seconds",
            "Critical_Zone",
            "Hazard_Level",
            "Detections_Count",
            "Best_Quality_Score",
            "FFmpeg_Extraction_Command",
        ])

        for idx, ev in enumerate(events, 1):
            dur = max(1, ev["end_sec"] - ev["start_sec"])
            start_fmt = format_mmss(ev["start_sec"])
            end_fmt = format_mmss(ev["end_sec"])
            clip_name = f"event_{idx:03d}_{ev['clip_file']}_clip.mp4"
            cmd = f'ffmpeg -ss {start_fmt} -to {end_fmt} -i "D:\\raw_footage\\{ev["clip_file"]}.mp4" -c copy "clippings\\{clip_name}"'

            writer.writerow([
                f"EVT-D{day_num:02d}-{idx:03d}",
                ev["clip_file"],
                ev["start_ts"],
                ev["end_ts"],
                start_fmt,
                end_fmt,
                dur,
                ev["zone_name"],
                ev["hazard"],
                ev["detection_count"],
                round(ev["max_quality"], 1) if ev["max_quality"] else "N/A",
                cmd,
            ])

    print(f"[OK] Generated {len(events)} video clipping events in: {output_csv}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-url", default=os.environ.get("DATABASE_URL"))
    parser.add_argument("--out", default="Day1_Persona_Video_Clipping_Index.csv")
    parser.add_argument("--camera-id", default="IPC56")
    parser.add_argument("--batch-id", default=None)
    parser.add_argument("--day", type=int, default=1)
    args = parser.parse_args()
    generate_clipping_csv(args.db_url, args.out, args.camera_id, args.batch_id, args.day)
