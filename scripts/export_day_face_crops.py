import argparse
import base64
import os
from pathlib import Path
from sqlalchemy import create_engine, text

def export_crops(db_url, day=2, out_base="/app/data"):
    batch_id = f"batch_30d_day_{day:02d}"
    out_dir = Path(out_base) / f"day{day:02d}_all_face_crops"
    out_dir.mkdir(parents=True, exist_ok=True)

    engine = create_engine(db_url)
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT id, timestamp, confidence, quality_score, face_image
            FROM detections
            WHERE batch_id = :batch_id AND face_image IS NOT NULL
            ORDER BY timestamp ASC
        """), {"batch_id": batch_id}).fetchall()

    print(f"Fetched {len(rows)} detections for {batch_id}. Saving images...")
    for i, r in enumerate(rows, 1):
        ts_str = str(r[1]).replace(":", "-").replace(" ", "_")
        q = int(r[3]) if r[3] is not None else 0
        c = int(r[2]) if r[2] is not None else 0
        fn = out_dir / f"face_{i:04d}_{ts_str}_q{q}_conf{c}.jpg"
        img_bytes = base64.b64decode(r[4])
        with open(fn, "wb") as f:
            f.write(img_bytes)

    print(f"[SUCCESS] Exported {len(rows)} face crops to {out_dir}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-url", default="postgresql://postgres:postgrespassword@postgres:5432/facial_ops")
    parser.add_argument("--day", type=int, default=2)
    parser.add_argument("--out-base", default="/app/data")
    args = parser.parse_args()
    export_crops(args.db_url, args.day, args.out_base)

