import json
from pathlib import Path

with open(r'D:\facial\data\30day_personas\30day_personas_master.json', 'r', encoding='utf-8') as f:
    master = json.load(f)

print('Keys in master:', list(master.keys()))
print('Total personas:', len(master['personas']))

# Let's inspect the top 15 personas
for p in master['personas'][:15]:
    pid = p['persona_id']
    dets = p['total_detections']
    days = p['days_active_count']
    first = p['first_seen']
    last = p['last_seen']
    contacts = p['zone_direct_contacts']
    shifts = p['shift_distribution']
    print(f"{pid:<10} | Detections: {dets:<6} | Days: {days:<2} | {first} -> {last} | Contacts: {contacts} | Shifts: {shifts}")

