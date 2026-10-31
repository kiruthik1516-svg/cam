"""
Manifest and Forensic Audit Generation for Engine v2.
"""
from typing import List, Dict, Any
import os
import csv
import json
from datetime import datetime

def export_day_manifest_csv(incidents: List[Dict[str, any]], output_csv_path: str):
    """Exports standardized incident evidence manifest."""
    os.makedirs(os.path.dirname(output_csv_path), exist_ok=True)
    fieldnames = [
        "incident_id",
        "day",
        "start_time",
        "peak_time",
        "end_time",
        "duration_sec",
        "zone_id",
        "zone_name",
        "severity",
        "interaction_type",
        "active_hand",
        "min_wrist_distance_px",
        "track_id",
        "clip_filename",
        "snapshot_filename"
    ]

    with open(output_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for inc in incidents:
            writer.writerow({
                "incident_id": inc["incident_id"],
                "day": inc["day"],
                "start_time": inc["start_time"].strftime("%Y-%m-%d %H:%M:%S"),
                "peak_time": inc["peak_time"].strftime("%Y-%m-%d %H:%M:%S"),
                "end_time": inc["end_time"].strftime("%Y-%m-%d %H:%M:%S"),
                "duration_sec": f"{inc['duration_sec']:.1f}",
                "zone_id": inc["zone_id"],
                "zone_name": inc["zone_name"],
                "severity": inc["severity"],
                "interaction_type": inc["interaction_type"],
                "active_hand": inc.get("active_hand", "N/A"),
                "min_wrist_distance_px": f"{inc.get('min_wrist_dist', 0.0):.1f}",
                "track_id": inc.get("track_id", "TRK-001"),
                "clip_filename": os.path.basename(inc.get("clip_path", "")),
                "snapshot_filename": os.path.basename(inc.get("snapshot_path", ""))
            })

def default_serializer(obj):
    if isinstance(obj, (datetime, )):
        return obj.isoformat()
    if hasattr(obj, "tolist"):
        return obj.tolist()
    return str(obj)

def export_day_summary_json(incidents: List[Dict[str, Any]], output_json_path: str, metadata: Dict[str, Any]):
    """Exports comprehensive forensic JSON summary."""
    os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
    payload = {
        "metadata": metadata,
        "total_incidents": len(incidents),
        "incidents": incidents
    }
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=default_serializer)
