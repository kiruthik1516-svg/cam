import os
from sqlalchemy import create_engine, text
from pathlib import Path

env_file = Path("D:/facial/.env")
db_url = None
with open(env_file, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line.startswith("DATABASE_URL="):
            db_url = line.split("=", 1)[1].strip("'\"\r\n\t ")
            break

print(f"Connecting to: {db_url.split('@')[1] if '@' in db_url else 'db'}...")
engine = create_engine(db_url)
with engine.connect() as conn:
    res = conn.execute(text("SELECT batch_id, camera_id, COUNT(*) FROM detections GROUP BY batch_id, camera_id")).fetchall()
    print("Found batches:")
    for r in res:
        print(f"  batch_id: '{r[0]}' | camera_id: '{r[1]}' | count: {r[2]}")

