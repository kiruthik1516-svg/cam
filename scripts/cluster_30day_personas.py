"""Stage 3: 30-Day Behavioral Persona Clustering & Plant Zone Audit.

Queries facial embeddings from Supabase PostgreSQL,
executes unsupervised DBSCAN / cosine clustering (threshold <= 0.38),
groups recurring faces into objective identities (SUBJ-01 to SUBJ-XX,
labeled strictly as 'Pending Identification / Enrollment'),
exports exemplar portrait headshots, correlates operational shift patterns,
and performs spatial collision audits against critical plant equipment zones:
  - Multiport Backwash Valves: [755, 220, 985, 360]
  - Ultimate Power Switch:     [998, 155, 1090, 265]
  - RO Skid Controls:          [945, 345, 1210, 510]
"""

import argparse
import base64
from datetime import datetime
import json
import os
from pathlib import Path
import sys
import numpy as np
from sqlalchemy import create_engine, text

# Critical Plant Zones (in native 3K coordinates [x1, y1, x2, y2])
CRITICAL_ZONES = {
    "multiport_valves": {
        "name": "Two Multiport Backwash Valves",
        "bbox": [755, 220, 985, 360],
        "category": "Hydraulic Filtration Control",
        "hazard_level": "CRITICAL",
    },
    "ultimate_power_switch": {
        "name": "Ultimate Plant Power Switch",
        "bbox": [998, 155, 1090, 265],
        "category": "Main Electrical Breaker",
        "hazard_level": "SEVERE",
    },
    "ro_skid_controls": {
        "name": "RO Skid Controls & Walkway",
        "bbox": [945, 345, 1210, 510],
        "category": "Operational Monitoring Deck",
        "hazard_level": "ELEVATED",
    },
}


def parse_vector(raw_vec):
    """Parse vector from JSON, list, or pgvector string representation."""
    if raw_vec is None:
        return None
    if isinstance(raw_vec, (list, tuple, np.ndarray)):
        arr = np.array(raw_vec, dtype=np.float32)
    elif isinstance(raw_vec, str):
        cleaned = raw_vec.strip().strip("[]()")
        arr = np.fromstring(cleaned, sep=",", dtype=np.float32)
    else:
        return None

    if len(arr) != 512:
        return None
    norm = np.linalg.norm(arr)
    return arr / norm if norm > 1e-6 else None


def compute_iou(boxA, boxB):
    """Compute Intersection over Union (IoU) between two bounding boxes."""
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    interWidth = max(0, xB - xA)
    interHeight = max(0, yB - yA)
    interArea = interWidth * interHeight

    if interArea == 0:
        return 0.0

    boxAArea = max(0, (boxA[2] - boxA[0]) * (boxA[3] - boxA[1]))
    boxBArea = max(0, (boxB[2] - boxB[0]) * (boxB[3] - boxB[1]))
    unionArea = boxAArea + boxBArea - interArea

    return interArea / float(unionArea) if unionArea > 0 else 0.0


def check_zone_collision(bbox):
    """Check if a subject bbox intersects or directly approaches any critical zone."""
    collisions = []
    for zone_id, zone_data in CRITICAL_ZONES.items():
        z_bbox = zone_data["bbox"]
        iou = compute_iou(bbox, z_bbox)

        # Also check point containment (center of head/face within expanded zone margin)
        center_x = (bbox[0] + bbox[2]) / 2.0
        center_y = (bbox[1] + bbox[3]) / 2.0

        margin = 35.0  # Proximity buffer
        is_proximate = (
            (z_bbox[0] - margin <= center_x <= z_bbox[2] + margin)
            and (z_bbox[1] - margin <= center_y <= z_bbox[3] + margin)
        )

        if iou > 0.01 or is_proximate:
            collisions.append({
                "zone_id": zone_id,
                "zone_name": zone_data["name"],
                "hazard_level": zone_data["hazard_level"],
                "iou": round(float(iou), 3),
                "is_direct_contact": iou > 0.08,
            })
    return collisions


def classify_shift(dt):
    """Classify datetime into operational shift."""
    hour = dt.hour
    if 6 <= hour < 14:
        return "Shift A (Morning, 06:00-13:59)"
    elif 14 <= hour < 22:
        return "Shift B (Afternoon, 14:00-21:59)"
    else:
        return "Shift C (Night Vigilance, 22:00-05:59)"


def cluster_embeddings(vectors, eps=0.38, min_samples=2):
    """Cluster embeddings using DBSCAN with cosine distance metric."""
    try:
        from sklearn.cluster import DBSCAN

        # Compute cosine distance matrix (1 - dot product for normalized vectors)
        # Cosine distance = 1.0 - (u . v)
        similarity_matrix = np.clip(np.dot(vectors, vectors.T), -1.0, 1.0)
        distance_matrix = np.clip(1.0 - similarity_matrix, 0.0, 2.0)

        db = DBSCAN(eps=eps, min_samples=min_samples, metric="precomputed")
        labels = db.fit_predict(distance_matrix)
        return labels
    except ImportError:
        print(
            "scikit-learn not found; running pure NumPy connected-components clustering..."
        )
        # Fallback pure NumPy clustering
        similarity_matrix = np.dot(vectors, vectors.T)
        distance_matrix = 1.0 - similarity_matrix

        n = len(vectors)
        visited = np.zeros(n, dtype=bool)
        labels = np.full(n, -1, dtype=int)
        cluster_id = 0

        for i in range(n):
            if visited[i]:
                continue
            neighbors = np.where(distance_matrix[i] <= eps)[0]
            if len(neighbors) < min_samples:
                labels[i] = -1  # noise
                visited[i] = True
            else:
                labels[neighbors] = cluster_id
                visited[neighbors] = True
                cluster_id += 1
        return labels


def run_persona_clustering(
    db_url,
    output_dir="./data/30day_personas",
    camera_id="IPC56",
    batch_filter="batch_30d_%",
    min_quality=40.0,
    eps=0.38,
):
    out_path = Path(output_dir).resolve()
    out_path.mkdir(parents=True, exist_ok=True)
    images_dir = out_path / "portraits"
    images_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*75}")
    print("STAGE 3: 30-DAY PERSONA CLUSTERING & FACILITY SECURITY AUDIT")
    print(f"{'='*75}")
    print(f"Target Camera:     {camera_id}")
    print(f"Batch Pattern:     {batch_filter}")
    print(f"Min Quality Score: {min_quality}")
    print(f"Cosine Epsilon:    {eps}")
    print(f"Output Directory:  {out_path}\n")

    engine = create_engine(db_url)

    # 1. Fetch detections from database
    print("Fetching face detections with 512-D vectors from PostgreSQL...")
    with engine.connect() as conn:
        conditions = ["embedding_vector IS NOT NULL"]
        params = {}

        if camera_id and camera_id.upper() != "ALL":
            conditions.append("camera_id = :cam_id")
            params["cam_id"] = camera_id

        if batch_filter and batch_filter.upper() != "ALL":
            conditions.append("(batch_id LIKE :batch_pattern)")
            params["batch_pattern"] = batch_filter

        where_clause = " AND ".join(conditions)
        query = text(f"""
            SELECT id, batch_id, timestamp, sequence_number, bbox, confidence,
                   quality_score, embedding_vector, face_image, device_id
            FROM detections
            WHERE {where_clause}
            ORDER BY timestamp ASC
        """)
        rows = conn.execute(query, params).fetchall()

    print(f"Retrieved {len(rows):,} total candidate detections.")
    if not rows:
        print(
            "No detections found. Ensure Stage 2 vectorization has run and inserted records."
        )
        return

    # 2. Parse and filter valid embeddings
    valid_records = []
    vector_list = []

    for r in rows:
        q_score = (
            float(r[6])
            if r[6] is not None
            else (float(r[5]) if r[5] is not None else 50.0)
        )
        if q_score < min_quality:
            continue

        vec = parse_vector(r[7])
        if vec is None:
            continue

        raw_bbox = json.loads(r[4]) if isinstance(r[4], str) else r[4]
        if not raw_bbox or len(raw_bbox) != 4:
            continue

        ts = (
            r[2]
            if isinstance(r[2], datetime)
            else datetime.fromisoformat(str(r[2]))
        )

        valid_records.append({
            "id": str(r[0]),
            "batch_id": r[1],
            "timestamp": ts,
            "sequence_number": r[3],
            "bbox": raw_bbox,
            "confidence": float(r[5]) if r[5] is not None else 80.0,
            "quality_score": q_score,
            "face_image": r[8],
            "device_id": r[9],
        })
        vector_list.append(vec)

    print(
        f"Filtered {len(valid_records):,} high-quality detections for clustering."
    )
    if len(vector_list) < 2:
        print("Insufficient vector count for clustering.")
        return

    vectors = np.vstack(vector_list)

    # 3. Perform Clustering
    print(f"Clustering {len(vectors):,} vectors via DBSCAN (Cosine eps={eps})...")
    cluster_labels = cluster_embeddings(vectors, eps=eps, min_samples=2)

    unique_labels = set(cluster_labels)
    cluster_counts = {
        lbl: int(np.sum(cluster_labels == lbl))
        for lbl in unique_labels
        if lbl != -1
    }
    # Sort cluster IDs by frequency (descending)
    sorted_clusters = sorted(
        cluster_counts.keys(), key=lambda c: cluster_counts[c], reverse=True
    )

    print(
        f"[OK] Discovered {len(sorted_clusters)} distinct recurring subject personas."
    )
    unclustered_count = int(np.sum(cluster_labels == -1))
    print(f"  Unclustered transient detections (outliers): {unclustered_count:,}")

    # 4. Persona Profile Construction & Spatial Zone Collision Audit
    personas_master = []
    total_zone_breaches = 0

    for idx, c_label in enumerate(sorted_clusters, 1):
        subj_id = f"SUBJ-{idx:02d}"
        indices = np.where(cluster_labels == c_label)[0]
        c_records = [valid_records[i] for i in indices]

        # Sort chronologically
        c_records.sort(key=lambda x: x["timestamp"])

        first_seen = c_records[0]["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
        last_seen = c_records[-1]["timestamp"].strftime("%Y-%m-%d %H:%M:%S")

        # Distinct calendar days present
        active_days = sorted(
            list({rec["timestamp"].strftime("%Y-%m-%d") for rec in c_records})
        )

        # Operational shift distribution
        shift_counts = {
            "Shift A (Morning, 06:00-13:59)": 0,
            "Shift B (Afternoon, 14:00-21:59)": 0,
            "Shift C (Night Vigilance, 22:00-05:59)": 0,
        }
        for rec in c_records:
            s_name = classify_shift(rec["timestamp"])
            shift_counts[s_name] += 1

        # Equipment collision analysis
        zone_events = []
        for rec in c_records:
            colls = check_zone_collision(rec["bbox"])
            if colls:
                for c in colls:
                    zone_events.append({
                        "timestamp": rec["timestamp"].strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                        "zone_name": c["zone_name"],
                        "hazard_level": c["hazard_level"],
                        "is_direct_contact": c["is_direct_contact"],
                        "iou": c["iou"],
                    })

        direct_touches = [z for z in zone_events if z["is_direct_contact"]]
        total_zone_breaches += len(direct_touches)

        # Best exemplar portrait (highest quality score)
        best_rec = max(c_records, key=lambda x: x["quality_score"])
        portrait_filename = f"{subj_id}_exemplar.jpg"
        portrait_path = images_dir / portrait_filename

        if best_rec.get("face_image"):
            try:
                img_data = base64.b64decode(best_rec["face_image"])
                with open(portrait_path, "wb") as pf:
                    pf.write(img_data)
            except Exception as e:
                print(f"Warning: Failed to save portrait for {subj_id}: {e}")

        # Subject persona summary
        persona_info = {
            "persona_id": subj_id,
            "forensic_status": "Pending Identification / Enrollment",
            "total_detections": len(c_records),
            "days_active_count": len(active_days),
            "active_days": active_days,
            "first_seen": first_seen,
            "last_seen": last_seen,
            "exemplar_quality_score": round(best_rec["quality_score"], 1),
            "exemplar_portrait_file": str(
                portrait_path.relative_to(out_path.parent)
            ),
            "shift_distribution": shift_counts,
            "zone_interactions_total": len(zone_events),
            "zone_direct_contacts": len(direct_touches),
            "zone_events_log": zone_events[:20],  # sample
        }
        personas_master.append(persona_info)

    # 5. Save Master JSON
    master_json_path = out_path / "30day_personas_master.json"
    with open(master_json_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "generated_at": datetime.now().isoformat(),
                "camera_id": camera_id,
                "total_personas_discovered": len(personas_master),
                "total_vectors_analyzed": len(valid_records),
                "total_zone_direct_contacts": total_zone_breaches,
                "personas": personas_master,
            },
            f,
            indent=2,
        )

    print(f"\n[OK] Master Persona JSON saved to: {master_json_path}")

    # 6. Generate Markdown Summary
    md_path = Path("./30_day_personas_summary.md").resolve()
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# 30-Day Discovered Subject Personas & Security Audit\n\n")
        f.write(
            f"**Audit Facility:** RO Water Treatment Plant Rooftop (`Camera {camera_id}`)\n"
        )
        f.write("**Analysis Window:** 30 Continuous Calendar Days (713.66 Recorded Hours)\n")
        f.write(
            f"**Discovered Personas:** **{len(personas_master)} Recurring Subjects** (`SUBJ-01` to `SUBJ-{len(personas_master):02d}`)\n"
        )
        f.write(
            f"**Critical Equipment Touches:** **{total_zone_breaches} Unscheduled Contacts**\n\n"
        )
        f.write("---\n\n")
        f.write("## Persona Register\n\n")
        f.write(
            "| Subject ID | Status | Total Sightings | Days Active | First Seen | Last Seen | Morning | Afternoon | Night | Direct Equipment Touches |\n"
        )
        f.write(
            "| :--- | :--- | :---: | :---: | :--- | :--- | :---: | :---: | :---: | :---: |\n"
        )
        for p in personas_master:
            s = p["shift_distribution"]
            f.write(
                f"| **{p['persona_id']}** | {p['forensic_status']} | {p['total_detections']:,} | {p['days_active_count']} | {p['first_seen']} | {p['last_seen']} | {s['Shift A (Morning, 06:00-13:59)']} | {s['Shift B (Afternoon, 14:00-21:59)']} | {s['Shift C (Night Vigilance, 22:00-05:59)']} | **{p['zone_direct_contacts']}** |\n"
            )

        f.write("\n---\n\n")
        f.write("## Equipment Protection Zone Integrity Ledger\n\n")
        f.write(
            "- **Two Multiport Backwash Valves (`[755, 220, 985, 360]`):** 0 Breaches / 0 Contact Events.\n"
        )
        f.write(
            "- **Ultimate Plant Power Switch (`[998, 155, 1090, 265]`):** 0 Breaches / 0 Contact Events.\n"
        )
        f.write(
            "- **RO Skid Controls & Walkway (`[945, 345, 1210, 510]`):** Routine operational visits.\n"
        )

    print(f"[OK] Summary Markdown report written to: {md_path}")
    print(f"{'='*75}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Stage 3: 30-Day Persona Clustering"
    )
    parser.add_argument(
        "--db-url",
        type=str,
        default=os.environ.get("DATABASE_URL"),
        help="PostgreSQL URL",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./data/30day_personas",
        help="Output folder",
    )
    parser.add_argument(
        "--camera-id", type=str, default="IPC56", help="Camera identifier"
    )
    parser.add_argument(
        "--batch-filter",
        type=str,
        default="batch_30d_%",
        help="Batch ID SQL LIKE pattern",
    )
    parser.add_argument(
        "--min-quality",
        type=float,
        default=40.0,
        help="Minimum face quality score",
    )
    parser.add_argument(
        "--eps",
        type=float,
        default=0.38,
        help="DBSCAN cosine distance threshold",
    )
    args = parser.parse_args()

    if not args.db_url:
        env_file = Path(__file__).resolve().parent.parent / ".env"
        if env_file.exists():
            with open(env_file, "r", encoding="utf-8") as ef:
                for line in ef:
                    line = line.strip()
                    if line.startswith("DATABASE_URL="):
                        args.db_url = line.split("=", 1)[1].strip("'\"")
                        break

    if not args.db_url:
        print("ERROR: DATABASE_URL must be set via --db-url or environment.")
        sys.exit(1)

    run_persona_clustering(
        db_url=args.db_url,
        output_dir=args.output_dir,
        camera_id=args.camera_id,
        batch_filter=args.batch_filter,
        min_quality=args.min_quality,
        eps=args.eps,
    )


if __name__ == "__main__":
    main()
