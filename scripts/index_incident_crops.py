import pandas as pd
from pathlib import Path
from datetime import datetime

df = pd.read_csv('D:/facial/incident_evidence/extracted_incident_manifest.csv')

# Pre-index crops by day
crops_by_day = {}
for d in range(1, 31):
    cdir = Path(f"D:/facial/data/day{d:02d}_all_face_crops")
    crops_by_day[d] = []
    if cdir.exists():
        for f in cdir.glob("*.jpg"):
            parts = f.stem.split('_')
            if len(parts) >= 4:
                ts_str = f"{parts[2]} {parts[3].replace('-', ':')}"
                try:
                    dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                    q = int(parts[4].replace('q', '')) if len(parts) > 4 else 0
                    conf = int(parts[5].replace('conf', '')) if len(parts) > 5 else 0
                    crops_by_day[d].append((dt, q, conf, f))
                except:
                    pass

print(f"Pre-indexed crops across all 30 days.")

missing = []
matched_summary = []

for idx, r in df.iterrows():
    eid = str(r['Event_ID'])
    day = int(r['Day'])
    b_start = str(r['Buffered_Start']).strip()
    b_end = str(r['Buffered_End']).strip()
    date_str = f"2026-09-{day:02d}"
    if ' ' not in b_start:
        b_start = f"{date_str} {b_start}"
        b_end = f"{date_str} {b_end}"
    dt_start = datetime.strptime(b_start, "%Y-%m-%d %H:%M:%S")
    dt_end = datetime.strptime(b_end, "%Y-%m-%d %H:%M:%S")

    in_window = [c for c in crops_by_day[day] if dt_start <= c[0] <= dt_end]
    if not in_window:
        missing.append((eid, day, b_start, r['Extracted_Clip_File']))
    else:
        # Sort by highest quality & confidence
        best = sorted(in_window, key=lambda x: (x[1], x[2]), reverse=True)[0]
        dest_crop = Path(f"D:/facial/incident_evidence/verified_faces/{eid}_day{day:02d}_verified_face.jpg")
        dest_crop.parent.mkdir(parents=True, exist_ok=True)
        import shutil
        shutil.copy(best[3], dest_crop)
        matched_summary.append({
            'Event_ID': eid,
            'Day': day,
            'Crop_Count': len(in_window),
            'Best_Crop': str(dest_crop),
            'Best_Q': best[1],
            'Best_Conf': best[2]
        })

print(f"Total matched: {len(matched_summary)}, Missing: {len(missing)}")
for m in missing:
    print(f"Missing: {m}")

