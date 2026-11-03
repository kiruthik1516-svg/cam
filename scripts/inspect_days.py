import json

with open("D:/facial/data/30day_personas/30day_personas_master.json", "r", encoding="utf-8") as f:
    data = json.load(f)

for target_day, date_str in [(5, "2026-09-05"), (25, "2026-09-25")]:
    print(f"\n==================== DAY {target_day} ({date_str}) ====================")
    events = []
    for p in data.get("personas", []):
        pid = p["persona_id"]
        for ev in p.get("zone_events_log", []):
            ts = ev.get("timestamp", "")
            if ts.startswith(date_str):
                events.append((ts, pid, ev.get("zone_name"), ev.get("hazard_level"), ev.get("is_direct_contact")))
    
    events.sort(key=lambda x: x[0])
    print(f"Total raw zone events on Day {target_day}: {len(events)}")
    for ev in events[:30]:
        print(ev)
    if len(events) > 30:
        print(f"... and {len(events)-30} more events")
