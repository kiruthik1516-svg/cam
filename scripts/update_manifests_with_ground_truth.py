import os
import json
import pandas as pd
from pathlib import Path

def main():
    map_csv = Path("D:/facial/incident_evidence/179_incidents_biometric_mapping.csv")
    if not map_csv.exists():
        print(f"[ERROR] Mapping CSV not found: {map_csv}")
        return

    df_map = pd.read_csv(map_csv)
    manifest_csv = Path("D:/facial/incident_evidence/extracted_incident_manifest.csv")
    df_man = pd.read_csv(manifest_csv)

    # Build mapping dict: Event_ID -> {Matched_Real_Person, Cosine_Similarity, Face_Path}
    info_map = {}
    for _, r in df_map.iterrows():
        eid = str(r['Event_ID'])
        info_map[eid] = {
            'Real_Person_ID': r['Matched_Real_Person'],
            'ArcFace_Cosine_Sim': r['Cosine_Similarity'],
            'Biometric_Confidence': r['Match_Confidence'],
            'Verified_Face_Crop': f"incident_evidence/verified_faces/{Path(str(r['Face_Path'])).name}"
        }

    # Merge into manifest
    df_man['Real_Person_ID'] = df_man['Event_ID'].map(lambda x: info_map.get(str(x), {}).get('Real_Person_ID', 'UNKNOWN'))
    df_man['ArcFace_Cosine_Sim'] = df_man['Event_ID'].map(lambda x: info_map.get(str(x), {}).get('ArcFace_Cosine_Sim', 0.0))
    df_man['Biometric_Confidence'] = df_man['Event_ID'].map(lambda x: info_map.get(str(x), {}).get('Biometric_Confidence', 'N/A'))
    df_man['Verified_Face_Crop'] = df_man['Event_ID'].map(lambda x: info_map.get(str(x), {}).get('Verified_Face_Crop', ''))

    df_man.to_csv(manifest_csv, index=False)
    print(f"[OK] Updated {manifest_csv}")

    # Copy to brain artifact directory
    brain_dir = Path("C:/Users/mkiru/.gemini/antigravity/brain/9cd9e7a5-62c1-473e-9b1f-aa014627f6c9")
    df_man.to_csv(brain_dir / "extracted_incident_manifest.csv", index=False)
    print(f"[OK] Copied manifest to {brain_dir / 'extracted_incident_manifest.csv'}")

    # Update all 30 daily clipping index CSVs
    updated_indices = 0
    for day in range(1, 31):
        idx_file = Path(f"D:/facial/incident_evidence/day_{day:02d}/Day{day}_Persona_Video_Clipping_Index.csv")
        if idx_file.exists():
            df_day = pd.read_csv(idx_file)
            df_day['Real_Person_ID'] = df_day['Event_ID'].map(lambda x: info_map.get(str(x), {}).get('Real_Person_ID', 'UNKNOWN'))
            df_day['ArcFace_Cosine_Sim'] = df_day['Event_ID'].map(lambda x: info_map.get(str(x), {}).get('ArcFace_Cosine_Sim', 0.0))
            df_day.to_csv(idx_file, index=False)
            updated_indices += 1

    print(f"[OK] Updated {updated_indices} daily clipping index files with Real_Person_ID and ArcFace_Cosine_Sim.")

if __name__ == "__main__":
    main()

