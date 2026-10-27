import json
from pathlib import Path
from datetime import datetime

master_path = Path("D:/facial/data/30day_personas/30day_personas_master.json")
with open(master_path, "r", encoding="utf-8") as f:
    master = json.load(f)

# Check if OP-VALVE-01 already exists
exists = any(p["persona_id"] == "OP-VALVE-01" for p in master["personas"])

op_persona = {
    "persona_id": "OP-VALVE-01",
    "forensic_status": "Enrolled / Verified Operator",
    "total_detections": 28,
    "days_active_count": 1,
    "active_days": ["2026-09-01"],
    "first_seen": "2026-09-01 09:53:20",
    "last_seen": "2026-09-01 09:54:15",
    "exemplar_quality_score": 91.5,
    "exemplar_portrait_file": "30day_personas/portraits/OP-VALVE-01_exemplar.jpg",
    "shift_distribution": {
        "Shift A (Morning, 06:00-13:59)": 28,
        "Shift B (Afternoon, 14:00-21:59)": 0,
        "Shift C (Night Vigilance, 22:00-05:59)": 0
    },
    "zone_interactions_total": 1,
    "zone_direct_contacts": 1,
    "zone_events_log": [
        {
            "timestamp": "2026-09-01 09:53:38",
            "zone_name": "Two Multiport Backwash Valves",
            "hazard_level": "CRITICAL",
            "is_direct_contact": True,
            "iou": 0.142
        }
    ]
}

if exists:
    print("Updating existing OP-VALVE-01...")
    master["personas"] = [op_persona if p["persona_id"] == "OP-VALVE-01" else p for p in master["personas"]]
else:
    print("Enrolling new persona OP-VALVE-01...")
    # Insert right at top or appropriate index
    master["personas"].append(op_persona)
    master["total_personas_discovered"] = len(master["personas"])

with open(master_path, "w", encoding="utf-8") as f:
    json.dump(master, f, indent=2)

print(f"[OK] Master personas JSON updated. Total personas: {len(master['personas'])}")
