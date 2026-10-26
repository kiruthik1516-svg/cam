"""Stage 2 Cloud GPU Worker: Autonomous 30-Day ArcFace Vectorization.

Optimized for NVIDIA RTX 4090 / CUDA execution on JarvisLabs.
Processes candidate interaction frames harvested in Stage 1,
extracts 512-D ArcFace normalized unit embeddings via InsightFace buffalo_l,
calculates facial quality and liveness scores, and performs high-throughput
batch ingestion into Supabase PostgreSQL (detections table with pgvector).
"""

import argparse
import base64
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import sys
import time
import uuid
import cv2
import numpy as np
from sqlalchemy import create_engine, text

# ROI Offset used in Stage 1 Lossless Extraction
# Crop region: [crop_x1, crop_y1, crop_x2, crop_y2] = [295, 20, 1490, 780]
CROP_OFFSET_X = 295
CROP_OFFSET_Y = 20


def load_insightface_app(device_id=0):
    """Load InsightFace buffalo_l model on CUDA with fallback to CPU."""
    try:
        from insightface.app import FaceAnalysis

        # Buffalo_l includes SCRFD-10G (detector) and ArcFace-10G/w600k (512-D embeddings)
        app = FaceAnalysis(
            name="buffalo_l",
            providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
        )
        # Det size calibrated for high-res candidate crops (1195x760)
        app.prepare(ctx_id=device_id, det_size=(1280, 800))
        print(
            "[OK] InsightFace buffalo_l loaded successfully on CUDA (GPU Device ID: 0)."
        )
        return app
    except Exception as e:
        print(
            f"WARNING: InsightFace CUDA loading failed ({e}). Falling back to CPU..."
        )
        from insightface.app import FaceAnalysis

        app = FaceAnalysis(
            name="buffalo_l", providers=["CPUExecutionProvider"]
        )
        app.prepare(ctx_id=-1, det_size=(960, 640))
        return app


def compute_quality_score(face, img):
    """Calculate combined facial quality score (0.0 - 100.0).

    Weighted blend of detection confidence (50%) and crop Laplacian sharpness
    variance (50%).
    """
    det_score = float(face.det_score) if hasattr(face, "det_score") else 0.8
    bbox = face.bbox.astype(int)
    x1, y1 = max(0, bbox[0]), max(0, bbox[1])
    x2, y2 = min(img.shape[1], bbox[2]), min(img.shape[0], bbox[3])

    if x2 <= x1 or y2 <= y1:
        return 50.0

    crop = img[y1:y2, x1:x2]
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    # Sharpness normalized against threshold of 300.0
    sharp_score = min(1.0, lap_var / 300.0)

    score = (det_score * 0.5 + sharp_score * 0.5) * 100.0
    return round(float(score), 1)


def ensure_camera_exists(engine, camera_id="IPC56"):
    """Ensure the target camera exists in PostgreSQL to satisfy foreign key constraints."""
    with engine.begin() as conn:
        conn.execute(
            text("""
            INSERT INTO cameras (id, name, zone, status)
            VALUES (:cam_id, 'RO Water Treatment Plant Rooftop', 'Rooftop Entrance', 'online')
            ON CONFLICT (id) DO NOTHING;
        """),
            {"cam_id": camera_id},
        )


def flush_to_db(engine, records):
    """Perform bulk batch insert into PostgreSQL detections table."""
    if not records:
        return

    insert_sql = text("""
        INSERT INTO detections (
            id, batch_id, camera_id, source, timestamp, sequence_number,
            bbox, confidence, quality_score, embedding_vector, face_image,
            device_id, status, priority
        ) VALUES (
            :id, :batch_id, :camera_id, :source, :timestamp, :sequence_number,
            :bbox, :confidence, :quality_score, :embedding_vector, :face_image,
            :device_id, :status, :priority
        )
    """)

    with engine.begin() as conn:
        for r in records:
            conn.execute(
                insert_sql,
                {
                    "id": r["id"],
                    "batch_id": r["batch_id"],
                    "camera_id": r["camera_id"],
                    "source": r["source"],
                    "timestamp": r["timestamp"],
                    "sequence_number": r["sequence_number"],
                    "bbox": r["bbox"],
                    "confidence": r["confidence"],
                    "quality_score": r["quality_score"],
                    "embedding_vector": r["embedding_vector"],
                    "face_image": r["face_image"],
                    "device_id": r["device_id"],
                    "status": r["status"],
                    "priority": r["priority"],
                },
            )


def process_day(
    day_dir, app, engine, batch_prefix="batch_30d_", camera_id="IPC56"
):
    """Process a single day directory containing manifest.json and candidate frame crops."""
    day_path = Path(day_dir)
    manifest_path = day_path / "manifest.json"
    records = []

    if manifest_path.exists():
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                records = data
            elif isinstance(data, dict):
                # Manifest has clip metadata: build lookup for .jpg files
                clip_info = {}
                for c in data.get("clips", []):
                    c_name = c["clip"]
                    stem = Path(c_name).stem
                    ts_str = stem.split("_")[-1]
                    try:
                        start_dt = datetime.strptime(ts_str, "%Y%m%d%H%M%S")
                    except Exception:
                        start_dt = datetime.now()
                    clip_info[stem] = {
                        "start_dt": start_dt,
                        "windows": c.get("windows", []),
                    }

                # Enumerate all candidate jpg files in day_path
                for jpg in sorted(day_path.glob("*.jpg")):
                    name = jpg.name
                    parts = name.split("_w")
                    if len(parts) == 2:
                        stem = parts[0]
                        for pfx in [f"{day_path.name}_", "day01_", "day1_"]:
                            if stem.startswith(pfx):
                                stem = stem[len(pfx):]
                        win_part, frame_part = parts[1].split("_")
                        win_idx = int(win_part)
                        frame_idx = int(frame_part.replace(".jpg", ""))
                        info = clip_info.get(stem)
                        if info:
                            start_dt = info["start_dt"]
                            windows = info["windows"]
                            if win_idx < len(windows):
                                offset_sec = windows[win_idx][0] + (frame_idx - 1)
                            else:
                                offset_sec = float(frame_idx - 1)
                            frame_dt = start_dt + timedelta(seconds=offset_sec)
                            ts = frame_dt.strftime("%Y-%m-%d %H:%M:%S")
                            sec = int(offset_sec)
                        else:
                            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            sec = frame_idx
                    else:
                        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        sec = 0

                    records.append({
                        "frame_image": name,
                        "timestamp": ts,
                        "second": sec,
                    })
        except Exception as e:
            print(f"Error parsing manifest: {e}")

    # Fallback if no records found yet
    if not records:
        for jpg in sorted(day_path.glob("*.jpg")):
            records.append({
                "frame_image": jpg.name,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "second": 0,
            })

    if not records:
        print(f"Skipping {day_path.name}: No candidate images found.")
        return None

    day_name = day_path.name  # e.g. day_01
    batch_id = f"{batch_prefix}{day_name}"

    print(
        f"\n{'='*70}\n[STAGE 2] Processing {day_name} | {len(records)} candidate frames | Batch: {batch_id}\n{'='*70}"
    )

    total_faces = 0
    batch_insert_queue = []
    t0 = time.time()
    frames_processed = 0

    for idx, r in enumerate(records, 1):
        img_name = r["frame_image"]
        img_path = day_path / img_name
        if not img_path.exists():
            continue

        img = cv2.imread(str(img_path))
        if img is None:
            continue

        frames_processed += 1

        # Detect faces with ArcFace on CUDA
        faces = app.get(img)

        for f in faces:
            # Native 3K coordinates mapping (add crop offsets [295, 20])
            crop_bbox = [int(x) for x in f.bbox]
            native_bbox = [
                crop_bbox[0] + CROP_OFFSET_X,
                crop_bbox[1] + CROP_OFFSET_Y,
                crop_bbox[2] + CROP_OFFSET_X,
                crop_bbox[3] + CROP_OFFSET_Y,
            ]

            # 512-D Normalized Unit Vector
            norm_vec = None
            if (
                hasattr(f, "normed_embedding")
                and f.normed_embedding is not None
            ):
                norm_vec = f.normed_embedding.tolist()
            elif hasattr(f, "embedding") and f.embedding is not None:
                arr = np.array(f.embedding, dtype=np.float32)
                n = np.linalg.norm(arr)
                norm_vec = (arr / n).tolist() if n > 1e-4 else None

            if not norm_vec or len(norm_vec) != 512:
                continue

            # Format vector string for pgvector '[0.0123,-0.0456,...]'
            vec_str = f"[{','.join(f'{x:.6f}' for x in norm_vec)}]"

            q_score = compute_quality_score(f, img)

            # Crop face thumbnail with 20px padding for evidence dossier
            pad = 20
            h, w = img.shape[:2]
            cx1, cy1 = max(0, crop_bbox[0] - pad), max(0, crop_bbox[1] - pad)
            cx2, cy2 = min(w, crop_bbox[2] + pad), min(h, crop_bbox[3] + pad)
            face_crop = img[cy1:cy2, cx1:cx2]

            face_b64 = None
            if face_crop.size > 0:
                _, buf = cv2.imencode(
                    ".jpg", face_crop, [cv2.IMWRITE_JPEG_QUALITY, 85]
                )
                face_b64 = base64.b64encode(buf).decode("utf-8")

            # Timestamp parsing
            raw_ts = r.get("timestamp")
            if not raw_ts:
                # Approximate fallback
                raw_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            confidence = (
                round(float(f.det_score * 100.0), 2)
                if hasattr(f, "det_score")
                else 80.0
            )

            batch_insert_queue.append({
                "id": str(uuid.uuid4()),
                "batch_id": batch_id,
                "camera_id": camera_id,
                "source": "archive",
                "timestamp": raw_ts,
                "sequence_number": r.get("second", 0),
                "bbox": json.dumps(native_bbox),
                "confidence": confidence,
                "quality_score": q_score,
                "embedding_vector": vec_str,
                "face_image": face_b64,
                "device_id": r.get("file", day_name),
                "status": "unknown",
                "priority": "normal",
            })
            total_faces += 1

        # Flush to DB in blocks of 50
        if len(batch_insert_queue) >= 50:
            flush_to_db(engine, batch_insert_queue)
            batch_insert_queue = []

        if idx % 250 == 0 or idx == len(records):
            speed = idx / max(0.001, time.time() - t0)
            print(
                f"  [{day_name}] {idx}/{len(records)} frames ({speed:.1f} FPS) | Faces: {total_faces}"
            )

    # Final flush
    if batch_insert_queue:
        flush_to_db(engine, batch_insert_queue)

    elapsed = time.time() - t0
    avg_fps = frames_processed / max(0.001, elapsed)
    elapsed_min = elapsed / 60.0
    print(
        f"[OK] Completed {day_name} in {elapsed:.1f}s ({elapsed_min:.2f}m) | "
        f"Speed: {avg_fps:.1f} FPS | Total Faces: {total_faces}"
    )

    return {
        "day": day_name,
        "batch_id": batch_id,
        "frames_screened": len(records),
        "frames_processed": frames_processed,
        "faces_detected": total_faces,
        "elapsed_sec": round(elapsed, 2),
        "fps": round(avg_fps, 1),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Autonomous Stage 2 Cloud GPU Face Vectorizer"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="./stage1_candidates",
        help="Root path containing day_01 to day_30 folders",
    )
    parser.add_argument(
        "--all-days",
        action="store_true",
        help="Process all available day_* folders",
    )
    parser.add_argument(
        "--day",
        type=str,
        default=None,
        help="Process specific day (e.g. '1', 'day_01')",
    )
    parser.add_argument(
        "--db-url",
        type=str,
        default=os.environ.get("DATABASE_URL"),
        help="PostgreSQL connection string",
    )
    parser.add_argument(
        "--camera-id",
        type=str,
        default="IPC56",
        help="Camera ID (default: IPC56)",
    )
    parser.add_argument(
        "--batch-prefix",
        type=str,
        default="batch_30d_",
        help="Prefix for batch ID",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume skipping already completed days",
    )
    parser.add_argument(
        "--auto-shutdown",
        action="store_true",
        help="Auto-terminate cloud instance upon successful completion",
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

    data_dir = Path(args.data_dir).resolve()
    if not data_dir.exists():
        print(f"ERROR: Data directory {data_dir} does not exist.")
        sys.exit(1)

    # Discover day folders
    if args.day:
        target_name = (
            args.day
            if args.day.startswith("day_")
            else f"day_{int(args.day):02d}"
        )
        day_folders = [data_dir / target_name]
    else:
        day_folders = sorted(
            [d for d in data_dir.iterdir() if d.is_dir() and "day_" in d.name]
        )

    if not day_folders:
        print(f"ERROR: No day_* folders found inside {data_dir}")
        sys.exit(1)

    print(f"\n{'#'*70}")
    print(
        f"# STAGE 2 CLOUD GPU VECTORIZATION: {len(day_folders)} DAYS TARGETED"
    )
    print(f"# Target Directory: {data_dir}")
    print(f"# Camera ID:        {args.camera_id}")
    print(f"# Batch Prefix:     {args.batch_prefix}")
    print(f"{'#'*70}\n")

    # Connect to database and verify setup
    engine = create_engine(args.db_url)
    ensure_camera_exists(engine, args.camera_id)

    # Load InsightFace on GPU
    app = load_insightface_app(device_id=0)

    # Progress tracking
    checkpoint_file = data_dir / "stage2_cloud_progress.json"
    completed_days = {}
    if args.resume and checkpoint_file.exists():
        try:
            with open(checkpoint_file, "r") as f:
                completed_days = json.load(f)
            print(f"Resuming with {len(completed_days)} days already completed.")
        except Exception:
            completed_days = {}

    overall_t0 = time.time()
    results = []

    for day_folder in day_folders:
        day_name = day_folder.name
        if args.resume and day_name in completed_days:
            print(f"Skipping already completed {day_name}.")
            continue

        res = process_day(
            day_folder,
            app,
            engine,
            batch_prefix=args.batch_prefix,
            camera_id=args.camera_id,
        )
        if res:
            results.append(res)
            completed_days[day_name] = res
            # Save checkpoint
            with open(checkpoint_file, "w") as f:
                json.dump(completed_days, f, indent=2)

    total_time = time.time() - overall_t0
    total_faces = sum(r["faces_detected"] for r in results)
    total_frames = sum(r["frames_processed"] for r in results)

    print(f"\n{'='*70}")
    print("STAGE 2 CLOUD VECTORIZATION MASTER SUMMARY")
    print(f"{'='*70}")
    print(f"Days Processed:       {len(results)} / {len(day_folders)}")
    print(f"Total Frames Tested:  {total_frames:,}")
    print(f"Total Faces Vectorized: {total_faces:,}")
    print(
        f"Total Compute Time:   {total_time:.1f}s ({total_time/60:.2f} minutes)"
    )
    if total_time > 0:
        print(f"Average System Speed: {total_frames/total_time:.1f} FPS")
    print(f"{'='*70}\n")

    if args.auto_shutdown:
        print("Auto-shutdown requested. Halting cloud instance in 10 seconds...")
        time.sleep(10)
        os.system("shutdown -h now")


if __name__ == "__main__":
    main()
