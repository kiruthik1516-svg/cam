import os
import sys
import json
import numpy as np
from pathlib import Path
from datetime import datetime
from sqlalchemy import create_engine, text

# Load DATABASE_URL from .env
env_file = Path("D:/facial/.env")
db_url = None
if env_file.exists():
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("DATABASE_URL="):
                db_url = line.split("=", 1)[1].strip("'\"")
                break

if not db_url:
    print("[ERROR] DATABASE_URL not found in .env")
    sys.exit(1)

print(f"[OK] Database URL loaded.")

CRITICAL_ZONES = {
    "multiport_valves": {
        "name": "Two Multiport Backwash Valves",
        "bbox": [755, 220, 985, 360],
        "hazard_level": "CRITICAL"
    },
    "ultimate_power_switch": {
        "name": "Ultimate Plant Power Switch",
        "bbox": [998, 155, 1090, 265],
        "hazard_level": "SEVERE"
    },
    "ro_skid_controls": {
        "name": "RO Skid Controls & Walkway",
        "bbox": [945, 345, 1210, 510],
        "hazard_level": "ELEVATED"
    }
}

def parse_vector(raw_vec):
    if raw_vec is None: return None
    if isinstance(raw_vec, (list, tuple, np.ndarray)):
        arr = np.array(raw_vec, dtype=np.float32)
    elif isinstance(raw_vec, str):
        cleaned = raw_vec.strip().strip("[]()")
        arr = np.fromstring(cleaned, sep=",", dtype=np.float32)
    else: return None
    if len(arr) != 512: return None
    norm = np.linalg.norm(arr)
    return arr / norm if norm > 1e-6 else None

def compute_iou(boxA, boxB):
    xA, yA = max(boxA[0], boxB[0]), max(boxA[1], boxB[1])
    xB, yB = min(boxA[2], boxB[2]), min(boxA[3], boxB[3])
    interW, interH = max(0, xB - xA), max(0, yB - yA)
    interArea = interW * interH
    if interArea == 0: return 0.0
    boxAArea = max(0, (boxA[2] - boxA[0]) * (boxA[3] - boxA[1]))
    boxBArea = max(0, (boxB[2] - boxB[0]) * (boxB[3] - boxB[1]))
    union = boxAArea + boxBArea - interArea
    return interArea / float(union) if union > 0 else 0.0

def check_zone_collision(bbox):
    colls = []
    for zid, zdata in CRITICAL_ZONES.items():
        z_bbox = zdata["bbox"]
        iou = compute_iou(bbox, z_bbox)
        cx = (bbox[0] + bbox[2]) / 2.0
        cy = (bbox[1] + bbox[3]) / 2.0
        margin = 35.0
        is_prox = (z_bbox[0] - margin <= cx <= z_bbox[2] + margin) and (z_bbox[1] - margin <= cy <= z_bbox[3] + margin)
        if iou > 0.01 or is_prox:
            colls.append({
                "zone_name": zdata["name"],
                "hazard_level": zdata["hazard_level"],
                "is_direct_contact": iou > 0.08
            })
    return colls

engine = create_engine(db_url)
print("Querying PostgreSQL for detections...")
with engine.connect() as conn:
    query = text("""
        SELECT id, batch_id, timestamp, sequence_number, bbox, confidence,
               quality_score, embedding_vector, device_id
        FROM detections
        WHERE embedding_vector IS NOT NULL
          AND camera_id = 'IPC56'
          AND batch_id LIKE 'batch_30d_%'
        ORDER BY timestamp ASC
    """)
    rows = conn.execute(query).fetchall()

print(f"Retrieved {len(rows):,} total candidate detections.")

valid_records = []
vector_list = []
for r in rows:
    q_score = float(r[6]) if r[6] is not None else (float(r[5]) if r[5] is not None else 50.0)
    if q_score < 40.0: continue
    vec = parse_vector(r[7])
    if vec is None: continue
    raw_bbox = json.loads(r[4]) if isinstance(r[4], str) else r[4]
    if not raw_bbox or len(raw_bbox) != 4: continue
    ts = r[2] if isinstance(r[2], datetime) else datetime.fromisoformat(str(r[2]))
    valid_records.append({
        "id": str(r[0]),
        "batch_id": r[1],
        "timestamp": ts,
        "sequence_number": r[3],
        "bbox": raw_bbox,
        "confidence": float(r[5]) if r[5] is not None else 80.0,
        "quality_score": q_score,
        "device_id": r[8]
    })
    vector_list.append(vec)

vectors = np.vstack(vector_list)
print(f"Clustering {len(vectors):,} vectors via DBSCAN (Cosine eps=0.38)...")
from sklearn.cluster import DBSCAN
euclidean_eps = float(np.sqrt(2.0 * 0.38))
db = DBSCAN(eps=euclidean_eps, min_samples=2, metric="euclidean", n_jobs=-1)
cluster_labels = db.fit_predict(vectors)

unique_labels = set(cluster_labels)
cluster_counts = {lbl: int(np.sum(cluster_labels == lbl)) for lbl in unique_labels if lbl != -1}
sorted_clusters = sorted(cluster_counts.keys(), key=lambda c: cluster_counts[c], reverse=True)

# Find cluster corresponding to SUBJ-02 (2nd cluster)
c_subj02 = sorted_clusters[1]
indices = np.where(cluster_labels == c_subj02)[0]
records_02 = [valid_records[i] for i in indices]
records_02.sort(key=lambda x: x["timestamp"])

print(f"\n[SUCCESS] SUBJ-02 total records: {len(records_02)}")

# Group records by calendar day and sessions
days_dict = {}
for rec in records_02:
    d_str = rec["timestamp"].strftime("%Y-%m-%d")
    if d_str not in days_dict:
        days_dict[d_str] = []
    days_dict[d_str].append(rec)

# Analyze sessions per day (break session if gap > 5 mins)
report_lines = []
csv_rows = []

for d_str, day_recs in sorted(days_dict.items()):
    sessions = []
    curr_sess = [day_recs[0]]
    for r in day_recs[1:]:
        gap = (r["timestamp"] - curr_sess[-1]["timestamp"]).total_seconds()
        if gap > 300: # 5 min gap
            sessions.append(curr_sess)
            curr_sess = [r]
        else:
            curr_sess.append(r)
    sessions.append(curr_sess)
    
    print(f"\n=== Date: {d_str} (Detections: {len(day_recs)}, Sessions: {len(sessions)}) ===")
    for s_idx, sess in enumerate(sessions, 1):
        t_start = sess[0]["timestamp"].strftime("%H:%M:%S")
        t_end = sess[-1]["timestamp"].strftime("%H:%M:%S")
        dwell_sec = int((sess[-1]["timestamp"] - sess[0]["timestamp"]).total_seconds()) + 1
        
        # Check equipment interactions
        touched = []
        for r in sess:
            colls = check_zone_collision(r["bbox"])
            for c in colls:
                if c["is_direct_contact"]:
                    touched.append(c["zone_name"])
        touched_str = ", ".join(sorted(list(set(touched)))) if touched else "Observation / Walkway"
        
        sess_str = f"  Session {s_idx:02d}: {t_start} - {t_end} (Dwell: {dwell_sec}s, Detections: {len(sess)}) | Equipment: {touched_str}"
        print(sess_str)
        
        csv_rows.append({
            "Date": d_str,
            "Day_Number": int(d_str.split("-")[2]),
            "Session_Number": s_idx,
            "Start_Time": t_start,
            "End_Time": t_end,
            "Start_Timestamp": sess[0]["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
            "End_Timestamp": sess[-1]["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
            "Dwell_Seconds": dwell_sec,
            "Detections_Count": len(sess),
            "Equipment_Interacted": touched_str,
            "Device_ID": sess[0]["device_id"]
        })

import pandas as pd
df_subj02 = pd.DataFrame(csv_rows)
out_csv = Path("D:/facial/SUBJ-02_Day1_Operator_30Day_Encounter_Log.csv")
df_subj02.to_csv(out_csv, index=False)
print(f"\n[SAVED] {out_csv} ({len(df_subj02)} sessions across {len(days_dict)} days)")

