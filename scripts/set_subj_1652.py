import json
import pandas as pd
from pathlib import Path
import shutil

print("Standardizing to SUBJ-1652...")

# 1. Portrait files
p_x = Path("D:/facial/data/30day_personas/portraits/SUBJ-X_exemplar.jpg")
p_1652 = Path("D:/facial/data/30day_personas/portraits/SUBJ-1652_exemplar.jpg")
if p_x.exists():
    shutil.copy2(str(p_x), str(p_1652))
    p_x.unlink(missing_ok=True)
    print(f"[OK] Renamed {p_x.name} -> {p_1652.name}")

brain_dir = Path("C:/Users/mkiru/.gemini/antigravity/brain/8c6e85a2-8ea1-4c6c-bb23-a9aed5b45fc6")
if (brain_dir / "SUBJ-X_exemplar.jpg").exists():
    shutil.copy2(str(brain_dir / "SUBJ-X_exemplar.jpg"), str(brain_dir / "SUBJ-1652_exemplar.jpg"))
    (brain_dir / "SUBJ-X_exemplar.jpg").unlink(missing_ok=True)
    print(f"[OK] Renamed brain artifact to SUBJ-1652_exemplar.jpg")

# 2. Master JSON
master_path = Path("D:/facial/data/30day_personas/30day_personas_master.json")
with open(master_path, "r", encoding="utf-8") as f:
    master = json.load(f)

for p in master["personas"]:
    if p["persona_id"] == "SUBJ-X":
        p["persona_id"] = "SUBJ-1652"
        p["exemplar_portrait_file"] = "30day_personas/portraits/SUBJ-1652_exemplar.jpg"

with open(master_path, "w", encoding="utf-8") as f:
    json.dump(master, f, indent=2)
print("[OK] Updated 30day_personas_master.json with SUBJ-1652")

# 3. Day 1 Clipping Indexes
for p in [Path("D:/facial/Day1_Persona_Video_Clipping_Index.csv"), Path("D:/facial/incident_evidence/day_01/Day1_Persona_Video_Clipping_Index.csv")]:
    if p.exists():
        df = pd.read_csv(p)
        df["Personas_Involved"] = df["Personas_Involved"].replace("SUBJ-X", "SUBJ-1652")
        df.to_csv(p, index=False)
        print(f"[OK] Updated {p} with SUBJ-1652")

# 4. Day 1 Audit Sheets
for p in [Path("D:/facial/Day1_Manual_Surveillance_Audit_Sheet.csv"), Path("D:/facial/incident_evidence/day_01/Day1_Manual_Surveillance_Audit_Sheet.csv")]:
    if p.exists():
        df = pd.read_csv(p)
        df["Reviewer_Comments"] = df["Reviewer_Comments"].astype(str).str.replace("SUBJ-X", "SUBJ-1652")
        df.to_csv(p, index=False)
        print(f"[OK] Updated {p} with SUBJ-1652")

# 5. Manifest
p_man = Path("D:/facial/incident_evidence/extracted_incident_manifest.csv")
if p_man.exists():
    df_man = pd.read_csv(p_man)
    df_man["Personas"] = df_man["Personas"].replace("SUBJ-X", "SUBJ-1652")
    df_man.to_csv(p_man, index=False)
    print(f"[OK] Updated {p_man} with SUBJ-1652")

# 6. Master Personas Behavioral Register CSV
p_reg = Path("D:/facial/30_Day_Master_Personas_Behavioral_Register.csv")
if p_reg.exists():
    df_reg = pd.read_csv(p_reg)
    df_reg["Persona_ID"] = df_reg["Persona_ID"].replace("SUBJ-X", "SUBJ-1652")
    df_reg["Exemplar_Portrait_Path"] = df_reg["Exemplar_Portrait_Path"].str.replace("SUBJ-X", "SUBJ-1652")
    df_reg.to_csv(p_reg, index=False)
    print(f"[OK] Updated {p_reg} with SUBJ-1652")

# 7. Markdown Reports
for rep_p in [Path("D:/facial/30_day_unique_people_behavioral_timeline_report.md"), brain_dir / "30_day_unique_people_behavioral_timeline_report.md"]:
    if rep_p.exists():
        with open(rep_p, "r", encoding="utf-8") as f:
            content = f.read()
        content = content.replace("SUBJ-X", "SUBJ-1652")
        with open(rep_p, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[OK] Updated {rep_p} with SUBJ-1652")

