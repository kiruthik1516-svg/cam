import urllib.request
import socket
import os
from pathlib import Path
from sqlalchemy import create_engine, text

def run_checks():
    checks = {}

    # 1. Frontend Web Dashboard
    try:
        with urllib.request.urlopen("http://217.18.55.230:3000", timeout=5) as r:
            checks["Frontend Dashboard (Port 3000)"] = (r.status == 200, f"HTTP {r.status} OK")
    except Exception as e:
        checks["Frontend Dashboard (Port 3000)"] = (False, str(e))

    # 2. Backend REST API
    try:
        with urllib.request.urlopen("http://217.18.55.230:1223/health", timeout=5) as r:
            checks["Backend Health API (Port 1223)"] = (r.status == 200, f"HTTP {r.status} OK")
    except Exception as e:
        checks["Backend Health API (Port 1223)"] = (False, str(e))

    # 3. PostgreSQL pgvector
    try:
        engine = create_engine(
            "postgresql://postgres:postgrespassword@217.18.55.230:5432/facial_ops",
            connect_args={"connect_timeout": 5}
        )
        with engine.connect() as conn:
            row = conn.execute(text("SELECT count(*) FROM detections;")).fetchone()
            d1_cnt = conn.execute(text("SELECT count(*) FROM detections WHERE batch_id = 'batch_30d_day_01';")).fetchone()
            d2_cnt = conn.execute(text("SELECT count(*) FROM detections WHERE batch_id = 'batch_30d_day_02';")).fetchone()
            checks["PostgreSQL Database (Port 5432)"] = (
                True,
                f"{row[0]:,} total detections (Day 1: {d1_cnt[0]:,}, Day 2: {d2_cnt[0]:,})"
            )
    except Exception as e:
        checks["PostgreSQL Database (Port 5432)"] = (False, str(e))

    # 4. Deliverables on Local Disk
    files_to_check = [
        ("Day 1 Clipping Index CSV", Path("D:/facial/Day1_Persona_Video_Clipping_Index.csv")),
        ("Day 2 Clipping Index CSV", Path("D:/facial/Day2_Persona_Video_Clipping_Index.csv")),
        ("30-Day Master Personas JSON", Path("D:/facial/data/30day_personas/30day_personas_master.json")),
        ("30-Day Personas Summary Markdown", Path("D:/facial/30_day_personas_summary.md")),
        ("Day 1 Manual Audit Sheet CSV", Path("D:/facial/Day1_Manual_Surveillance_Audit_Sheet.csv")),
    ]
    for label, p in files_to_check:
        checks[label] = (p.exists() and p.stat().st_size > 0, f"{p.stat().st_size:,} bytes" if p.exists() else "Missing")

    # 5. Local Face Crops and Portraits
    p_d1 = Path("D:/facial/data/day01_all_face_crops")
    p_d2 = Path("D:/facial/data/day02_all_face_crops")
    p_portraits = Path("D:/facial/data/30day_personas/portraits")

    cnt_d1 = len(list(p_d1.glob("*.jpg"))) if p_d1.exists() else 0
    cnt_d2 = len(list(p_d2.glob("*.jpg"))) if p_d2.exists() else 0
    cnt_portraits = len(list(p_portraits.glob("*.jpg"))) if p_portraits.exists() else 0

    checks["Day 1 Face Crops (Local)"] = (cnt_d1 == 2117, f"{cnt_d1:,} images (Target: 2,117)")
    checks["Day 2 Face Crops (Local)"] = (cnt_d2 == 2390, f"{cnt_d2:,} images (Target: 2,390)")
    checks["Persona Portrait Headshots"] = (cnt_portraits == 210, f"{cnt_portraits:,} portraits (Target: 210)")

    print("\n" + "=" * 80)
    print("SURVEILLANCE INFRASTRUCTURE & DELIVERABLES HEALTH CHECK")
    print("=" * 80)
    all_ok = True
    for k, (ok, detail) in checks.items():
        status = "[PASS]" if ok else "[FAIL]"
        if not ok:
            all_ok = False
        print(f"{status}  {k:<36} : {detail}")
    print("=" * 80)
    print(f"OVERALL STATUS: {'ALL CHECKS PASSED - PRODUCTION READY' if all_ok else 'SOME CHECKS FAILED'}\n")
    return all_ok

if __name__ == "__main__":
    run_checks()

