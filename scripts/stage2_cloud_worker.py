import os
import sys
import time
import json
import base64
import argparse
import numpy as np
from pathlib import Path
import cv2
from sqlalchemy import create_engine, text

def load_insightface_app(device_id=0):
    try:
        from insightface.app import FaceAnalysis
        app = FaceAnalysis(name="buffalo_l", providers=["CUDAExecutionProvider", "CPUExecutionProvider"])
        app.prepare(ctx_id=device_id, det_size=(2880, 1620)) # Native 3K resolution detection
        print("InsightFace loaded successfully with Native 3K detection size on CUDA.")
        return app
    except Exception as e:
        print(f"Warning: InsightFace CUDA loading failed ({e}). Falling back to CPU.")
        from insightface.app import FaceAnalysis
        app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
        app.prepare(ctx_id=-1, det_size=(1920, 1080))
        return app

def compute_quality_score(face, img):
    # InsightFace detector score (0-1)
    det_score = float(face.det_score) if hasattr(face, "det_score") else 0.8
    # Crop face area
    bbox = face.bbox.astype(int)
    x1, y1, x2, y2 = max(0, bbox[0]), max(0, bbox[1]), min(img.shape[1], bbox[2]), min(img.shape[0], bbox[3])
    if x2 <= x1 or y2 <= y1:
        return 50.0
    crop = img[y1:y2, x1:x2]
    # Laplacian variance for sharpness
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    sharp_score = min(1.0, lap_var / 300.0)
    
    # Combined score 0 - 100%
    score = (det_score * 0.5 + sharp_score * 0.5) * 100.0
    return round(float(score), 1)

def run_extraction(manifest_path, db_url, batch_id):
    manifest_file = Path(manifest_path)
    if not manifest_file.exists():
        print(f"ERROR: Manifest file {manifest_file} not found.")
        return
        
    with open(manifest_file, "r") as f:
        records = json.load(f)
        
    print(f"Loaded {len(records)} active candidate frames from {manifest_file}.")
    base_dir = manifest_file.parent
    
    engine = create_engine(db_url)
    app = load_insightface_app()
    
    total_faces = 0
    batch_insert_queue = []
    t0 = time.time()
    
    for idx, r in enumerate(records, 1):
        img_name = r["frame_image"]
        img_path = base_dir / img_name
        if not img_path.exists():
            continue
            
        img = cv2.imread(str(img_path))
        if img is None:
            continue
            
        # Detect faces at native resolution
        faces = app.get(img)
        
        for f in faces:
            bbox = [int(x) for x in f.bbox]
            # ArcFace normalized vector
            norm_vec = f.normed_embedding.tolist() if hasattr(f, "normed_embedding") and f.normed_embedding is not None else None
            if not norm_vec and hasattr(f, "embedding"):
                arr = np.array(f.embedding, dtype=np.float32)
                n = np.linalg.norm(arr)
                norm_vec = (arr / n).tolist() if n > 1e-4 else None
                
            if not norm_vec:
                continue
                
            q_score = compute_quality_score(f, img)
            
            # Crop face thumbnail (with padding)
            pad = 20
            h, w = img.shape[:2]
            cx1, cy1 = max(0, bbox[0] - pad), max(0, bbox[1] - pad)
            cx2, cy2 = min(w, bbox[2] + pad), min(h, bbox[3] + pad)
            face_crop = img[cy1:cy2, cx1:cx2]
            
            # Encode base64 JPEG
            _, buf = cv2.imencode(".jpg", face_crop, [cv2.IMWRITE_JPEG_QUALITY, 85])
            face_b64 = base64.b64encode(buf).decode("utf-8")
            
            batch_insert_queue.append({
                "batch_id": batch_id,
                "timestamp": r.get("timestamp", "2026-09-01 00:00:00"),
                "sequence_number": r.get("second", 0),
                "bbox": json.dumps(bbox),
                "confidence": round(float(f.det_score * 100.0), 2) if hasattr(f, "det_score") else 80.0,
                "quality_score": q_score,
                "embedding_vector": norm_vec,
                "face_image": face_b64,
                "device_id": r.get("file", "unknown")
            })
            total_faces += 1
            
        # Flush to DB every 50 faces
        if len(batch_insert_queue) >= 50:
            flush_to_db(engine, batch_insert_queue)
            batch_insert_queue = []
            
        if idx % 100 == 0:
            fps_speed = idx / (time.time() - t0)
            print(f"Processed {idx}/{len(records)} frames ({fps_speed:.1f} FPS) | Faces detected: {total_faces}")
            
    # Final flush
    if batch_insert_queue:
        flush_to_db(engine, batch_insert_queue)
        
    elapsed = time.time() - t0
    print(f"Extraction completed in {elapsed:.1f}s ({elapsed/60:.2f}m) | Total faces extracted: {total_faces}")

def flush_to_db(engine, records):
    with engine.begin() as conn:
        for r in records:
            conn.execute(text("""
                INSERT INTO detections (
                    batch_id, timestamp, sequence_number, bbox, confidence,
                    quality_score, embedding_vector, face_image, device_id
                ) VALUES (
                    :batch_id, :timestamp, :sequence_number, :bbox, :confidence,
                    :quality_score, :embedding_vector, :face_image, :device_id
                )
            """), {
                "batch_id": r["batch_id"],
                "timestamp": r["timestamp"],
                "sequence_number": r["sequence_number"],
                "bbox": r["bbox"],
                "confidence": r["confidence"],
                "quality_score": r["quality_score"],
                "embedding_vector": json.dumps(r["embedding_vector"]),
                "face_image": r["face_image"],
                "device_id": r["device_id"]
            })

def main():
    parser = argparse.ArgumentParser(description="Stage 2 Cloud GPU Face Extractor")
    parser.add_argument("--manifest", type=str, required=True, help="Path to manifest.json")
    parser.add_argument("--db-url", type=str, default=os.environ.get("DATABASE_URL"), help="PostgreSQL connection string")
    parser.add_argument("--batch-id", type=str, required=True, help="Ingestion batch ID")
    parser.add_argument("--auto-shutdown", action="store_true", help="Auto terminate instance on completion")
    args = parser.parse_args()
    
    if not args.db_url:
        print("ERROR: DATABASE_URL must be specified.")
        return
        
    print(f"Starting Stage 2 Cloud Extraction for Batch: {args.batch_id}")
    run_extraction(args.manifest, args.db_url, args.batch_id)
    
    if args.auto_shutdown:
        print("Executing cloud shutdown sequence...")
        os.system("shutdown -h now")

if __name__ == "__main__":
    main()

