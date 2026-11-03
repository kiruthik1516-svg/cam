import csv
import os

def read_manifest(path):
    print(f"\n--- {path} ---")
    if not os.path.exists(path):
        print("DOES NOT EXIST")
        return
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        print(f"Total rows: {len(rows)}")
        for r in rows:
            print(dict(r))

read_manifest("D:/facial/incident_evidence_v2/day_05/Day05_Incident_Manifest.csv")
read_manifest("D:/facial/incident_evidence/day_05/Day5_Persona_Video_Clipping_Index.csv")
read_manifest("D:/facial/incident_evidence_v2/day_25/Day25_Incident_Manifest.csv")
read_manifest("D:/facial/incident_evidence/day_25/Day25_Persona_Video_Clipping_Index.csv")

