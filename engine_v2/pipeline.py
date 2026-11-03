"""
Continuous HOI Incident Detection and Trimming Pipeline for Engine v2.
Standalone - keeps all legacy systems completely untouched.
"""
from typing import List, Dict, Tuple, Optional
from pathlib import Path
import os
import re
import cv2
import numpy as np
from datetime import datetime, timedelta

REPO_ROOT = Path(__file__).resolve().parent.parent
STAGE1_CANDIDATES_DIR = os.getenv("STAGE1_CANDIDATES_DIR", str(REPO_ROOT / "data" / "stage1_candidates"))
INCIDENT_EVIDENCE_DIR = os.getenv("INCIDENT_EVIDENCE_DIR", str(REPO_ROOT / "incident_evidence"))

from .config import (
    CCTV_MASTER_DIR,
    OUTPUT_MASTER_DIR,
    ASSET_ZONES,
    MIN_INTERACTION_DURATION_SEC,
    MERGE_INCIDENT_GAP_SEC,
    LEAD_IN_BUFFER_SEC,
    LEAD_OUT_BUFFER_SEC
)
from .detector import PoseInteractionDetector
from .geometry import render_pose_skeleton
from .trimmer import extract_incident_clip
from .manifest import export_day_manifest_csv, export_day_summary_json

def list_day_chunks(day_num: int, cctv_dir: str = CCTV_MASTER_DIR) -> List[Dict[str, any]]:
    """Discovers and chronologically indexes all video chunks for a day. Returns empty list if offline."""
    if not os.path.exists(cctv_dir):
        return []

    day_folder = os.path.join(cctv_dir, str(day_num))
    if not os.path.exists(day_folder):
        day_folder = os.path.join(cctv_dir, f"{day_num:02d}")
    if not os.path.exists(day_folder):
        return []

    files = [f for f in os.listdir(day_folder) if f.lower().endswith(".mp4")]
    chunks = []
    for f in files:
        m = re.search(r"(\d{14})\.mp4$", f)
        if not m:
            continue
        start_dt = datetime.strptime(m.group(1), "%Y%m%d%H%M%S")
        full_path = os.path.join(day_folder, f)
        
        cap = cv2.VideoCapture(full_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 81000.0
        duration_sec = frame_count / fps
        cap.release()

        end_dt = start_dt + timedelta(seconds=duration_sec)
        chunks.append({
            "path": full_path,
            "filename": f,
            "start_dt": start_dt,
            "end_dt": end_dt,
            "fps": fps,
            "frame_count": int(frame_count),
            "duration_sec": duration_sec
        })

    chunks.sort(key=lambda x: x["start_dt"])
    return chunks

def scan_single_chunk(chunk_info: Dict[str, any], detector: Optional[PoseInteractionDetector] = None) -> List[Dict[str, any]]:
    """
    Scans a single video chunk for equipment interactions using Adaptive Stride.
    Idle: 3.0s stride | Person Present: 1.0s stride | Interaction: 0.5s stride.
    """
    if detector is None:
        detector = PoseInteractionDetector()

    cap = cv2.VideoCapture(chunk_info["path"])
    fps = chunk_info["fps"]
    total_frames = chunk_info["frame_count"]
    total_duration = chunk_info["duration_sec"]

    raw_events = []
    sec = 0.0
    stride = 3.0

    while sec < total_duration:
        frame_idx = int(round(sec * fps))
        if frame_idx >= total_frames:
            break

        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if not ret:
            break

        current_dt = chunk_info["start_dt"] + timedelta(seconds=sec)

        # Fast motion gate and pose detector
        motion, detections = detector.process_frame(frame)
        has_person = len(detections) > 0
        has_interaction = False

        if motion and detections:
            # Check for multi-person corridor presence
            if len(detections) >= 2:
                has_corridor = any("ZONE_DOORWAY" in det.get("interactions", {}) or "ZONE_RO_SKID" in det.get("interactions", {}) for det in detections)
                if has_corridor:
                    has_interaction = True
                    raw_events.append({
                        "timestamp": current_dt,
                        "sec_offset": sec,
                        "frame_idx": frame_idx,
                        "chunk_path": chunk_info["path"],
                        "zone_id": "ZONE_DOORWAY",
                        "zone_name": "Terrace Entrance & Walkway Corridor",
                        "severity": "ELEVATED",
                        "interaction_type": "MULTI_PERSON_CORRIDOR_PRESENCE",
                        "wrist_contact": False,
                        "active_wrist": None,
                        "min_wrist_dist": 999.0,
                        "person_box": detections[0]["person_box"],
                        "keypoints": detections[0]["keypoints"],
                        "confidence": detections[0]["confidence"]
                    })

            for det in detections:
                interactions = det.get("interactions", {})
                for zone_id, eval_data in interactions.items():
                    # For ZONE_DOORWAY: capture multi-person, hardware contact, or dwell
                    if zone_id == "ZONE_DOORWAY" and len(detections) < 2 and not eval_data.get("wrist_contact"):
                        continue

                    has_interaction = True
                    raw_events.append({
                        "timestamp": current_dt,
                        "sec_offset": sec,
                        "frame_idx": frame_idx,
                        "chunk_path": chunk_info["path"],
                        "zone_id": zone_id,
                        "zone_name": ASSET_ZONES[zone_id].name,
                        "severity": ASSET_ZONES[zone_id].severity,
                        "interaction_type": eval_data["interaction_type"],
                        "wrist_contact": eval_data["wrist_contact"],
                        "active_wrist": eval_data["active_wrist"],
                        "min_wrist_dist": eval_data["min_wrist_dist"],
                        "person_box": det["person_box"],
                        "keypoints": det["keypoints"],
                        "confidence": det["confidence"]
                    })

        # Adaptive Stride Adjustment
        if has_interaction:
            stride = 0.5  # High temporal density during active contact
        elif has_person:
            stride = 1.0  # Medium density while person walks around
        else:
            stride = 3.0  # Fast sweep across empty room

        sec += stride

    cap.release()
    return raw_events

def cluster_raw_events(raw_events: List[Dict[str, any]], max_gap_sec: float = MERGE_INCIDENT_GAP_SEC) -> List[Dict[str, any]]:
    """
    Groups discrete detection timestamps into continuous incident sessions.
    Any equipment interactions occurring within max_gap_sec of each other
    belong to the SAME operational session, regardless of zone transitions.
    """
    if not raw_events:
        return []

    sorted_events = sorted(raw_events, key=lambda x: x["timestamp"])
    clusters = []
    current_cluster = [sorted_events[0]]

    for evt in sorted_events[1:]:
        prev_evt = current_cluster[-1]
        gap = (evt["timestamp"] - prev_evt["timestamp"]).total_seconds()

        # Session continuity: merge if person continues interacting within max_gap_sec
        if gap <= max_gap_sec:
            current_cluster.append(evt)
        else:
            clusters.append(current_cluster)
            current_cluster = [evt]

    if current_cluster:
        clusters.append(current_cluster)

    incidents = []
    for c in clusters:
        start_t = c[0]["timestamp"]
        end_t = c[-1]["timestamp"]
        dur = max(1.0, (end_t - start_t).total_seconds())

        is_micro_toggle = any(x["zone_id"] == "ZONE_SWITCH" or x.get("interaction_type") in ("INSTANT_MICRO_TOGGLE", "WRIST_CONTACT") for x in c)
        is_multi_person = any(x.get("interaction_type") == "MULTI_PERSON_CORRIDOR_PRESENCE" for x in c)

        if not is_micro_toggle and not is_multi_person and dur < MIN_INTERACTION_DURATION_SEC and len(c) < 2:
            continue

        # Severity hierarchy: Switch (SEVERE) > Valves (CRITICAL) > Multi-person Corridor (ELEVATED) > RO Skid (ELEVATED) > Doorway (INFORMATIONAL)
        has_switch = any(x["zone_id"] == "ZONE_SWITCH" for x in c)
        has_valves = any(x["zone_id"] == "ZONE_VALVES" for x in c)
        has_wrist = any(x["wrist_contact"] for x in c)

        if has_switch:
            primary_zone_id = "ZONE_SWITCH"
            severity = "SEVERE"
        elif has_valves:
            primary_zone_id = "ZONE_VALVES"
            severity = "CRITICAL"
        elif any(x.get("interaction_type") == "MULTI_PERSON_CORRIDOR_PRESENCE" for x in c):
            primary_zone_id = "ZONE_DOORWAY"
            severity = "ELEVATED"
        elif any(x["zone_id"] == "ZONE_RO_SKID" for x in c):
            primary_zone_id = "ZONE_RO_SKID"
            severity = "ELEVATED"
        else:
            primary_zone_id = "ZONE_DOORWAY"
            severity = "INFORMATIONAL"

        matching_zone_events = [x for x in c if x["zone_id"] == primary_zone_id]
        if not matching_zone_events:
            matching_zone_events = c
        best_evt = min(matching_zone_events, key=lambda x: x["min_wrist_dist"])

        if is_multi_person and primary_zone_id == "ZONE_DOORWAY":
            interaction_type = "MULTI_PERSON_CORRIDOR_PRESENCE"
        elif any(x.get("interaction_type") == "INSTANT_MICRO_TOGGLE" for x in c):
            interaction_type = "INSTANT_MICRO_TOGGLE"
        elif has_wrist:
            interaction_type = "WRIST_CONTACT"
        else:
            interaction_type = "PROXIMITY_DWELL"

        zones_touched = sorted(list(set(x["zone_id"].replace("ZONE_", "") for x in c)))
        zone_label = "_".join(zones_touched)

        active_hands = set(x["active_wrist"] for x in c if x["active_wrist"])
        active_hand_str = " / ".join(sorted(list(active_hands))) if active_hands else "BODY"

        incidents.append({
            "start_time": start_t,
            "peak_time": best_evt["timestamp"],
            "end_time": end_t,
            "duration_sec": dur,
            "zone_id": primary_zone_id,
            "zone_name": ASSET_ZONES[primary_zone_id].name,
            "zones_touched": zone_label,
            "severity": severity,
            "interaction_type": interaction_type,
            "active_hand": active_hand_str,
            "min_wrist_dist": best_evt["min_wrist_dist"],
            "peak_event": best_evt
        })

    return incidents

def scan_day_candidate_frames(day_num: int, detector: Optional[PoseInteractionDetector] = None) -> List[Dict[str, any]]:
    """
    Offline fallback scanner: Iterates stage-1 candidate frames for day_num,
    using adaptive sampling and fast motion filtration.
    """
    if detector is None:
        detector = PoseInteractionDetector()

    idx_path = os.path.join(INCIDENT_EVIDENCE_DIR, f"day_{day_num:02d}", f"Day{day_num}_Extracted_Frames_Timestamp_Index.csv")
    cand_dir = os.path.join(STAGE1_CANDIDATES_DIR, f"day_{day_num:02d}")

    if not os.path.exists(idx_path) or not os.path.exists(cand_dir):
        return []

    import pandas as pd
    df = pd.read_csv(idx_path)
    df['dt'] = pd.to_datetime(df['Calculated_WallClock_Timestamp'])
    df = df.sort_values('dt').reset_index(drop=True)

    raw_events = []
    step = 2
    i = 0
    total = len(df)

    while i < total:
        row = df.iloc[i]
        fname = row['Frame_File_Name']
        fpath = os.path.join(cand_dir, fname)
        current_dt = row['dt'].to_pydatetime()

        if not os.path.exists(fpath):
            i += step
            continue

        frame = cv2.imread(fpath)
        if frame is None:
            i += step
            continue

        motion, detections = detector.process_frame(frame)
        has_person = len(detections) > 0
        has_interaction = False

        if motion and detections:
            # Check for multi-person corridor presence
            if len(detections) >= 2:
                has_corridor = any("ZONE_DOORWAY" in det.get("interactions", {}) or "ZONE_RO_SKID" in det.get("interactions", {}) for det in detections)
                if has_corridor:
                    has_interaction = True
                    raw_events.append({
                        "timestamp": current_dt,
                        "sec_offset": 0.0,
                        "frame_idx": i,
                        "chunk_path": fpath,
                        "frame_file": fname,
                        "zone_id": "ZONE_DOORWAY",
                        "zone_name": "Terrace Entrance & Walkway Corridor",
                        "severity": "ELEVATED",
                        "interaction_type": "MULTI_PERSON_CORRIDOR_PRESENCE",
                        "wrist_contact": False,
                        "active_wrist": None,
                        "min_wrist_dist": 999.0,
                        "person_box": detections[0]["person_box"],
                        "keypoints": detections[0]["keypoints"],
                        "confidence": detections[0]["confidence"]
                    })

            for det in detections:
                interactions = det.get("interactions", {})
                for zone_id, eval_data in interactions.items():
                    if zone_id == "ZONE_DOORWAY" and len(detections) < 2 and not eval_data.get("wrist_contact"):
                        continue

                    has_interaction = True
                    raw_events.append({
                        "timestamp": current_dt,
                        "sec_offset": 0.0,
                        "frame_idx": i,
                        "chunk_path": fpath,
                        "frame_file": fname,
                        "zone_id": zone_id,
                        "zone_name": ASSET_ZONES[zone_id].name,
                        "severity": ASSET_ZONES[zone_id].severity,
                        "interaction_type": eval_data["interaction_type"],
                        "wrist_contact": eval_data["wrist_contact"],
                        "active_wrist": eval_data["active_wrist"],
                        "min_wrist_dist": eval_data["min_wrist_dist"],
                        "person_box": det["person_box"],
                        "keypoints": det["keypoints"],
                        "confidence": det["confidence"]
                    })

        # Adaptive step
        if has_interaction:
            step = 1
        elif has_person:
            step = 1
        else:
            step = 3

        i += step

    return raw_events

def process_day(
    day_num: int,
    output_base_dir: str = OUTPUT_MASTER_DIR,
    max_workers: int = 1,
    hour_range: Optional[Tuple[int, int]] = None,
    cctv_dir: Optional[str] = None
) -> List[Dict[str, any]]:
    """
    Executes full Engine v2 pipeline for a specified day.
    Outputs all clips and manifests to output_base_dir/day_XX.
    """
    day_output_dir = os.path.join(output_base_dir, f"day_{day_num:02d}")
    os.makedirs(day_output_dir, exist_ok=True)

    target_cctv_dir = cctv_dir or CCTV_MASTER_DIR
    print(f"[Engine v2] Scanning Day {day_num} video chunks in {target_cctv_dir}...", flush=True)
    chunks = list_day_chunks(day_num, cctv_dir=target_cctv_dir)
    print(f"[Engine v2] Found {len(chunks)} physical chunks for Day {day_num}", flush=True)

    if hour_range is not None:
        h_start, h_end = hour_range
        filtered = [cf for cf in chunks if h_start <= cf["start_dt"].hour <= h_end or h_start <= cf["end_dt"].hour <= h_end]
        print(f"[Engine v2] Hour filter [{h_start:02d}:00 - {h_end:02d}:59]: Scanning {len(filtered)} / {len(chunks)} chunks.", flush=True)
        chunks_to_scan = filtered
    else:
        chunks_to_scan = chunks

    detector = PoseInteractionDetector()
    all_raw_events = []

    if not chunks:
        print(f"[Engine v2] Master physical CCTV drive offline. Engaging Stage-1 Candidate Frame Scanner for Day {day_num}...", flush=True)
        all_raw_events = scan_day_candidate_frames(day_num, detector=detector)
    else:
        for idx, cf in enumerate(chunks_to_scan):
            fname = cf["filename"]
            events = scan_single_chunk(cf, detector=detector)
            if events:
                print(f"   -> [{idx+1}/{len(chunks_to_scan)}] {fname}: Found {len(events)} interactions", flush=True)
                all_raw_events.extend(events)
            else:
                print(f"   -> [{idx+1}/{len(chunks_to_scan)}] {fname}: Clean (0 interactions)", flush=True)

    print(f"[Engine v2] Total raw interaction detections for Day {day_num}: {len(all_raw_events)}", flush=True)
    incidents = cluster_raw_events(all_raw_events)
    print(f"[Engine v2] Clustered into {len(incidents)} confirmed incident events.", flush=True)

    # Generate Evidence Clips and Snapshots
    final_incidents = []
    for inc_idx, inc in enumerate(incidents):
        inc_id = f"EVT-V2-D{day_num:02d}-{inc_idx+1:03d}"
        zone_slug = inc.get("zones_touched", inc["zone_id"].replace("ZONE_", ""))
        time_slug = inc["peak_time"].strftime("%Y%m%d_%H%M%S")
        
        clip_fname = f"Day{day_num:02d}_{inc_id}_{inc['severity']}_{zone_slug}_{time_slug}.mp4"
        snap_fname = f"Day{day_num:02d}_{inc_id}_{inc['severity']}_{zone_slug}_{time_slug}_Snapshot.jpg"
        
        clip_path = os.path.join(day_output_dir, clip_fname)
        snap_path = os.path.join(day_output_dir, snap_fname)

        # Extract snapshot at peak interaction frame
        peak = inc["peak_event"]
        frame = None
        cpath = peak.get("chunk_path", "")
        if cpath and os.path.exists(cpath):
            if cpath.lower().endswith((".jpg", ".jpeg", ".png")):
                frame = cv2.imread(cpath)
            else:
                cap = cv2.VideoCapture(cpath)
                cap.set(cv2.CAP_PROP_POS_FRAMES, peak["frame_idx"])
                ret, frame = cap.read()
                cap.release()
        elif peak.get("frame_file"):
            cand_p = os.path.join(STAGE1_CANDIDATES_DIR, f"day_{day_num:02d}", peak["frame_file"])
            if os.path.exists(cand_p):
                frame = cv2.imread(cand_p)

        if frame is not None:
            annotated = render_pose_skeleton(
                frame,
                peak["keypoints"],
                person_box=peak["person_box"],
                highlight_wrists=peak["wrist_contact"]
            )
            hz = ASSET_ZONES[inc["zone_id"]].hardware_box
            cv2.rectangle(annotated, (hz[0], hz[1]), (hz[2], hz[3]), (0, 0, 255), 3)
            cv2.putText(
                annotated,
                f"{inc['zone_name']} [{inc['severity']}]",
                (hz[0], max(30, hz[1] - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 0, 255),
                2
            )
            cv2.imwrite(snap_path, annotated)

        # Extract continuous video clip with FFmpeg
        print(f"[Engine v2] Trimming incident clip: {clip_fname} (Peak: {inc['peak_time'].strftime('%H:%M:%S')})...", flush=True)
        extract_incident_clip(
            chunk_files=chunks,
            incident_start_dt=inc["start_time"],
            incident_end_dt=inc["end_time"],
            output_mp4_path=clip_path,
            lead_in_sec=LEAD_IN_BUFFER_SEC,
            lead_out_sec=LEAD_OUT_BUFFER_SEC,
            day_num=day_num
        )

        inc_record = dict(inc)
        inc_record["incident_id"] = inc_id
        inc_record["day"] = day_num
        inc_record["clip_path"] = clip_path
        inc_record["snapshot_path"] = snap_path
        inc_record["track_id"] = f"TRK-{inc_idx+1:03d}"
        final_incidents.append(inc_record)

    # Export Manifest & Summary
    manifest_csv = os.path.join(day_output_dir, f"Day{day_num:02d}_Incident_Manifest.csv")
    summary_json = os.path.join(day_output_dir, f"Day{day_num:02d}_Forensic_Summary.json")

    export_day_manifest_csv(final_incidents, manifest_csv)
    export_day_summary_json(final_incidents, summary_json, metadata={
        "engine": "Engine v2 (HOI Keypoint Fusion)",
        "day": day_num,
        "processed_at": datetime.now().isoformat(),
        "total_chunks_scanned": len(chunks)
    })

    print(f"[Engine v2] Day {day_num} complete! Manifest exported to: {manifest_csv}", flush=True)
    return final_incidents
