from sqlalchemy import create_engine, text

DB_URL = "postgresql://postgres:postgrespassword@100.97.114.117:5432/facial_ops"

def check():
    try:
        engine = create_engine(DB_URL, connect_args={"connect_timeout": 5})
        with engine.connect() as conn:
            tot = conn.execute(text("SELECT count(*) FROM detections;")).fetchone()[0]
            print(f"TOTAL_DETECTIONS: {tot}")
            rows = conn.execute(text("SELECT batch_id, count(*) FROM detections GROUP BY batch_id ORDER BY batch_id;")).fetchall()
            for b_id, cnt in rows:
                print(f"{b_id}: {cnt}")
    except Exception as e:
        print(f"DB_ERROR: {e}")

if __name__ == '__main__':
    check()
