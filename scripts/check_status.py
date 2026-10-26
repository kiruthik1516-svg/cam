from sqlalchemy import create_engine, text

DB_URL = "postgresql://postgres:postgrespassword@100.97.114.117:5432/facial_ops"

def check():
    try:
        engine = create_engine(DB_URL, connect_args={"connect_timeout": 5})
        with engine.connect() as conn:
            tot = conn.execute(text("SELECT count(*) FROM detections;")).fetchone()[0]
            d1 = conn.execute(text("SELECT count(*) FROM detections WHERE batch_id = 'batch_30d_day_01';")).fetchone()[0]
            d2 = conn.execute(text("SELECT count(*) FROM detections WHERE batch_id = 'batch_30d_day_02';")).fetchone()[0]
            d3 = conn.execute(text("SELECT count(*) FROM detections WHERE batch_id = 'batch_30d_day_03';")).fetchone()[0]
            d4 = conn.execute(text("SELECT count(*) FROM detections WHERE batch_id = 'batch_30d_day_04';")).fetchone()[0]
            d5 = conn.execute(text("SELECT count(*) FROM detections WHERE batch_id = 'batch_30d_day_05';")).fetchone()[0]
            d6 = conn.execute(text("SELECT count(*) FROM detections WHERE batch_id = 'batch_30d_day_06';")).fetchone()[0]
            d7 = conn.execute(text("SELECT count(*) FROM detections WHERE batch_id = 'batch_30d_day_07';")).fetchone()[0]
            d8 = conn.execute(text("SELECT count(*) FROM detections WHERE batch_id = 'batch_30d_day_08';")).fetchone()[0]
            d9 = conn.execute(text("SELECT count(*) FROM detections WHERE batch_id = 'batch_30d_day_09';")).fetchone()[0]
            d10 = conn.execute(text("SELECT count(*) FROM detections WHERE batch_id = 'batch_30d_day_10';")).fetchone()[0]
            d11 = conn.execute(text("SELECT count(*) FROM detections WHERE batch_id = 'batch_30d_day_11';")).fetchone()[0]
            
            d11_time = conn.execute(text("SELECT min(timestamp), max(timestamp) FROM detections WHERE batch_id = 'batch_30d_day_11';")).fetchone()
            
            print(f"TOTAL_DETECTIONS: {tot}")
            print(f"DAY1: {d1}")
            print(f"DAY2: {d2}")
            print(f"DAY3: {d3}")
            print(f"DAY4: {d4}")
            print(f"DAY5: {d5}")
            print(f"DAY6: {d6}")
            print(f"DAY7: {d7}")
            print(f"DAY8: {d8}")
            print(f"DAY9: {d9}")
            print(f"DAY10: {d10}")
            print(f"DAY11: {d11}")
            print(f"DAY11_TIMESTAMPS: {d11_time[0]} -> {d11_time[1]}")
    except Exception as e:
        print(f"DB_ERROR: {e}")

if __name__ == '__main__':
    check()
