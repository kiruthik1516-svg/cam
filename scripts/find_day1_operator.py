import json
from pathlib import Path

with open(r'D:\facial\data\30day_personas_master.json', 'r') as f:
    data = json.load(f)

print(f"Total personas: {len(data['personas'])}")

day1_0950_matches = []
for p in data['personas']:
    pid = p['persona_id']
    for ev in p.get('zone_events_log', []):
        ts = ev.get('timestamp', '')
        if '2026-09-01' in ts and ('09:4' in ts or '09:5' in ts or '10:0' in ts):
            day1_0950_matches.append((pid, ts, ev))

print(f"Total matches in Day 1 09:40-10:05 window: {len(day1_0950_matches)}")
for pid, ts, ev in day1_0950_matches:
    print(f"  {pid} | {ts} | Zone: {ev.get('zone')} | DirectContact: {ev.get('direct_contact')}")

