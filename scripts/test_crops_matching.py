import pandas as pd
from pathlib import Path
from datetime import datetime

df = pd.read_csv('D:/facial/incident_evidence/extracted_incident_manifest.csv')
print(f"Total incidents: {len(df)}")

found_in_crops = 0
incident_crop_map = {}

for idx, r in df.iterrows():
    eid = str(r['Event_ID'])
    day = int(r['Day'])
    crops_dir = Path(f"D:/facial/data/day{day:02d}_all_face_crops")
    if not crops_dir.exists():
        continue
    
    b_start = str(r['Buffered_Start']).strip()
    b_end = str(r['Buffered_End']).strip()
    
    # parse timestamp
    try:
        if ' ' in b_start:
            dt_start = datetime.strptime(b_start, '%Y-%m-%d %H:%M:%S')
            dt_end = datetime.strptime(b_end, '%Y-%m-%d %H:%M:%S')
        else:
            # prepend date
            date_str = f"2026-09-{day:02d}"
            dt_start = datetime.strptime(f"{date_str} {b_start}", '%Y-%m-%d %H:%M:%S')
            dt_end = datetime.strptime(f"{date_str} {b_end}", '%Y-%m-%d %H:%M:%S')
    except Exception as e:
        continue
        
    matched_crops = []
    for f in crops_dir.glob('*.jpg'):
        parts = f.stem.split('_')
        # face_0001_2026-09-01_01-29-56_q87_conf75
        if len(parts) >= 4:
            ts_str = f"{parts[2]} {parts[3].replace('-', ':')}"
            try:
                dt_crop = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S')
                if dt_start <= dt_crop <= dt_end:
                    matched_crops.append(f)
            except:
                pass
    if matched_crops:
        found_in_crops += 1
        incident_crop_map[eid] = matched_crops

print(f"Incidents with pre-extracted crops in exact time window: {found_in_crops} / {len(df)}")

