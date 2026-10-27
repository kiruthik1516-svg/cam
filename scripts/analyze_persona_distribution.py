import json
import pandas as pd
from collections import Counter

with open(r'D:\facial\data\30day_personas\30day_personas_master.json', 'r', encoding='utf-8') as f:
    master = json.load(f)

personas = master['personas']
print(f"Total personas: {len(personas)}")

# Breakdown by detection count
t1 = [p for p in personas if p['total_detections'] >= 50]
t2 = [p for p in personas if 10 <= p['total_detections'] < 50]
t3 = [p for p in personas if 2 <= p['total_detections'] < 10]
t4 = [p for p in personas if p['total_detections'] == 1]

print(f"Tier 1 (Core Staff >= 50 detections): {len(t1)}")
print(f"Tier 2 (Regular Personnel 10-49 detections): {len(t2)}")
print(f"Tier 3 (Occasional / Visitors 2-9 detections): {len(t3)}")
print(f"Tier 4 (Single Detections): {len(t4)}")

# Zone direct contacts
contacts = [p for p in personas if p['zone_direct_contacts'] > 0]
print(f"Personas with direct equipment contacts: {len(contacts)}")
for p in contacts:
    print(f"  {p['persona_id']}: {p['zone_direct_contacts']} contacts, days={p['days_active_count']}, detections={p['total_detections']}")

# Shift counts
shift_totals = Counter()
for p in personas:
    for s, c in p['shift_distribution'].items():
        shift_totals[s] += c
print("\nOverall shift distribution of detections:")
for s, c in shift_totals.items():
    print(f"  {s}: {c:,}")

