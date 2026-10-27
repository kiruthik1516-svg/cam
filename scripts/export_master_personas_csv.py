import json
import pandas as pd
from pathlib import Path

with open(r'D:\facial\data\30day_personas\30day_personas_master.json', 'r', encoding='utf-8') as f:
    master = json.load(f)

personas = master['personas']

rows = []
for p in personas:
    pid = p['persona_id']
    dets = p['total_detections']
    days = p['days_active_count']
    first = p['first_seen']
    last = p['last_seen']
    sa = p['shift_distribution'].get('Shift A (Morning, 06:00-13:59)', 0)
    sb = p['shift_distribution'].get('Shift B (Afternoon, 14:00-21:59)', 0)
    sc = p['shift_distribution'].get('Shift C (Night Vigilance, 22:00-05:59)', 0)
    contacts = p['zone_direct_contacts']
    interactions = p['zone_interactions_total']
    q_score = p['exemplar_quality_score']
    portrait = p['exemplar_portrait_file']
    
    tier = "Tier 1 (Core Staff)" if dets >= 50 else ("Tier 2 (Regular)" if dets >= 10 else "Tier 3 (Occasional)")
    risk = "CRITICAL" if contacts > 20 else ("ELEVATED" if contacts > 0 else "LOW")

    rows.append({
        "Persona_ID": pid,
        "Classification_Tier": tier,
        "Total_Detections": dets,
        "Days_Active_Count": days,
        "First_Seen_Timestamp": first,
        "Last_Seen_Timestamp": last,
        "Shift_A_Morning_Detections": sa,
        "Shift_B_Afternoon_Detections": sb,
        "Shift_C_Night_Detections": sc,
        "Direct_Equipment_Contacts": contacts,
        "Total_Zone_Interactions": interactions,
        "Exemplar_Quality_Score": q_score,
        "Exemplar_Portrait_Path": portrait,
        "Facility_Risk_Rating": risk
    })

df = pd.DataFrame(rows)
df.sort_values(by="Total_Detections", ascending=False, inplace=True)
out_csv = Path("D:/facial/30_Day_Master_Personas_Behavioral_Register.csv")
df.to_csv(out_csv, index=False)
print(f"[OK] Exported master personas register: {out_csv} ({len(df)} rows)")
