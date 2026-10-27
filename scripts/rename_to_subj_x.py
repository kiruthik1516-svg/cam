import json
import pandas as pd
from pathlib import Path
import shutil

# 1. Rename portrait file
p_old = Path("D:/facial/data/30day_personas/portraits/OP-VALVE-01_exemplar.jpg")
p_new = Path("D:/facial/data/30day_personas/portraits/SUBJ-X_exemplar.jpg")
if p_old.exists():
    shutil.copy2(str(p_old), str(p_new))
    print(f"[OK] Created {p_new}")

# Artifact portrait
brain_dir = Path("C:/Users/mkiru/.gemini/antigravity/brain/8c6e85a2-8ea1-4c6c-bb23-a9aed5b45fc6")
if (brain_dir / "OP-VALVE-01_exemplar.jpg").exists():
    shutil.copy2(str(brain_dir / "OP-VALVE-01_exemplar.jpg"), str(brain_dir / "SUBJ-X_exemplar.jpg"))
    print(f"[OK] Created brain artifact SUBJ-X_exemplar.jpg")

# 2. Update 30day_personas_master.json
master_path = Path("D:/facial/data/30day_personas/30day_personas_master.json")
with open(master_path, "r", encoding="utf-8") as f:
    master = json.load(f)

for p in master["personas"]:
    if p["persona_id"] == "OP-VALVE-01":
        p["persona_id"] = "SUBJ-X"
        p["forensic_status"] = "Pending Identification / Enrollment (Manual Review Recovery)"
        p["exemplar_portrait_file"] = "30day_personas/portraits/SUBJ-X_exemplar.jpg"

with open(master_path, "w", encoding="utf-8") as f:
    json.dump(master, f, indent=2)
print("[OK] Updated 30day_personas_master.json with SUBJ-X")

# 3. Update Day1_Persona_Video_Clipping_Index.csv
for p in [Path("D:/facial/Day1_Persona_Video_Clipping_Index.csv"), Path("D:/facial/incident_evidence/day_01/Day1_Persona_Video_Clipping_Index.csv")]:
    if p.exists():
        df = pd.read_csv(p)
        df["Personas_Involved"] = df["Personas_Involved"].replace("OP-VALVE-01", "SUBJ-X")
        df.to_csv(p, index=False)
        print(f"[OK] Updated {p} with SUBJ-X")

# 4. Update Day1_Manual_Surveillance_Audit_Sheet.csv
for p in [Path("D:/facial/Day1_Manual_Surveillance_Audit_Sheet.csv"), Path("D:/facial/incident_evidence/day_01/Day1_Manual_Surveillance_Audit_Sheet.csv")]:
    if p.exists():
        df = pd.read_csv(p)
        df["Reviewer_Comments"] = df["Reviewer_Comments"].astype(str).str.replace("OP-VALVE-01", "SUBJ-X")
        df.to_csv(p, index=False)
        print(f"[OK] Updated {p} with SUBJ-X")

# 5. Update extracted_incident_manifest.csv
p_man = Path("D:/facial/incident_evidence/extracted_incident_manifest.csv")
if p_man.exists():
    df_man = pd.read_csv(p_man)
    df_man["Personas"] = df_man["Personas"].replace("OP-VALVE-01", "SUBJ-X")
    df_man.to_csv(p_man, index=False)
    print(f"[OK] Updated {p_man} with SUBJ-X")

# 6. Update 30_Day_Master_Personas_Behavioral_Register.csv
p_reg = Path("D:/facial/30_Day_Master_Personas_Behavioral_Register.csv")
if p_reg.exists():
    df_reg = pd.read_csv(p_reg)
    df_reg["Persona_ID"] = df_reg["Persona_ID"].replace("OP-VALVE-01", "SUBJ-X")
    df_reg["Exemplar_Portrait_Path"] = df_reg["Exemplar_Portrait_Path"].str.replace("OP-VALVE-01", "SUBJ-X")
    df_reg.to_csv(p_reg, index=False)
    print(f"[OK] Updated {p_reg} with SUBJ-X")

# 7. Update 30_day_unique_people_behavioral_timeline_report.md
for rep_p in [Path("D:/facial/30_day_unique_people_behavioral_timeline_report.md"), brain_dir / "30_day_unique_people_behavioral_timeline_report.md"]:
    if rep_p.exists():
        with open(rep_p, "r", encoding="utf-8") as f:
            content = f.read()
        content = content.replace("OP-VALVE-01", "SUBJ-X")
        with open(rep_p, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[OK] Updated {rep_p} with SUBJ-X")

