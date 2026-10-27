import json
import pandas as pd
from pathlib import Path

# Load 30day_personas_master.json
with open(r'D:\facial\data\30day_personas_master.json', 'r') as f:
    master = json.load(f)

subj02 = None
for p in master['personas']:
    if p['persona_id'] == 'SUBJ-02':
        subj02 = p
        break

print(f"Persona: {subj02['persona_id']}")
print(f"Total Detections in Master JSON: {subj02.get('total_detections')}")
print(f"Active Days Count: {subj02.get('days_active_count')}")
print(f"Active Days List: {subj02.get('active_days')}")
print(f"Exemplar: {subj02.get('exemplar_portrait_file')}")
print(f"Shift distribution: {subj02.get('shift_distribution')}")
print(f"Zone interactions total: {subj02.get('zone_interactions_total')}")
print(f"Zone direct contacts: {subj02.get('zone_direct_contacts')}")

# Now let's scan all 30 clipping index CSVs for SUBJ-02
print("\n--- Scanning All 30 Persona Video Clipping Index CSVs for SUBJ-02 ---")
all_subj02_events = []
for day in range(1, 31):
    csv_path = Path(f"D:/facial/Day{day}_Persona_Video_Clipping_Index.csv")
    if not csv_path.exists():
        csv_path = Path(f"D:/facial/Day0{day}_Persona_Video_Clipping_Index.csv")
    if csv_path.exists():
        df = pd.read_csv(csv_path)
        # Check Personas_Involved
        m = df[df['Personas_Involved'].astype(str).str.contains('SUBJ-02', na=False)]
        for _, row in m.iterrows():
            all_subj02_events.append({
                'Day': f"Day {day:02d}",
                'Event_ID': row.get('Event_ID'),
                'Start_WallClock': row.get('Start_WallClock_Time'),
                'End_WallClock': row.get('End_WallClock_Time'),
                'Duration_Sec': row.get('Duration_Seconds'),
                'Critical_Zone': row.get('Critical_Zone'),
                'Hazard_Level': row.get('Hazard_Level'),
                'Personas_Involved': row.get('Personas_Involved'),
                'Detections': row.get('Detections_Count')
            })

df_events = pd.DataFrame(all_subj02_events)
print(f"Total Clipping Index Events involving SUBJ-02: {len(df_events)}")
if len(df_events) > 0:
    print(df_events[['Day', 'Event_ID', 'Start_WallClock', 'End_WallClock', 'Critical_Zone', 'Duration_Sec']].to_string())

# Also check zone_events_log in master JSON
print("\n--- Zone Events Log in Master JSON for SUBJ-02 ---")
z_log = subj02.get('zone_events_log', [])
print(f"Total Zone Events in Master JSON: {len(z_log)}")
for ev in z_log:
    print(f"  {ev.get('timestamp')} | Zone: {ev.get('zone')} | Contact: {ev.get('direct_contact')}")

