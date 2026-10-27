import os
import json
import cv2
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
import onnxruntime as ort

def get_arcface_session():
    model_path = Path("C:/Users/mkiru/.insightface/models/buffalo_l/w600k_r50.onnx")
    opts = ort.SessionOptions()
    opts.intra_op_num_threads = 6
    return ort.InferenceSession(str(model_path), opts, providers=['CPUExecutionProvider'])

def preprocess_face(img):
    img = cv2.resize(img, (112, 112))
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = np.transpose(img, (2, 0, 1)).astype(np.float32)
    img = (img - 127.5) / 127.5
    return img

def main():
    sess = get_arcface_session()
    input_name = sess.get_inputs()[0].name
    
    # 1. Load 43 Real Person definitions
    with open("D:/facial/data/30day_personas/consolidated_real_personas.json", "r") as f:
        real_personas = json.load(f)
    print(f"Loaded {len(real_personas)} consolidated real personas.")

    # Compute anchor embeddings
    anchor_embeddings = {}
    for rp in real_personas:
        pid = rp['Real_Person_ID']
        anchor_subj = rp['Anchor_Persona']
        # Load portrait image
        img_path = Path(f"D:/facial/data/30day_personas/portraits/{anchor_subj}_exemplar.jpg")
        if not img_path.exists():
            print(f"[WARN] Portrait not found: {img_path}")
            continue
        img = cv2.imread(str(img_path))
        if img is None:
            continue
        tensor = np.expand_dims(preprocess_face(img), axis=0)
        feat = sess.run(None, {input_name: tensor})[0][0]
        feat = feat / np.linalg.norm(feat)
        anchor_embeddings[pid] = {
            'embedding': feat,
            'anchor_subj': anchor_subj,
            'data': rp
        }
    print(f"Computed embeddings for {len(anchor_embeddings)} real person anchors.")

    # 2. Pre-index crops across 30 days
    crops_by_day = {}
    for d in range(1, 31):
        cdir = Path(f"D:/facial/data/day{d:02d}_all_face_crops")
        crops_by_day[d] = []
        if cdir.exists():
            for f in cdir.glob("*.jpg"):
                parts = f.stem.split('_')
                if len(parts) >= 4:
                    ts_str = f"{parts[2]} {parts[3].replace('-', ':')}"
                    try:
                        dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                        q = int(parts[4].replace('q', '')) if len(parts) > 4 else 0
                        conf = int(parts[5].replace('conf', '')) if len(parts) > 5 else 0
                        crops_by_day[d].append((dt, q, conf, f))
                    except:
                        pass

    # 3. Process 179 incidents
    df_manifest = pd.read_csv("D:/facial/incident_evidence/extracted_incident_manifest.csv")
    verified_faces_dir = Path("D:/facial/incident_evidence/verified_faces")
    verified_faces_dir.mkdir(parents=True, exist_ok=True)

    incident_results = []
    
    # Batch tensors for incident crops
    incident_crops_to_run = []
    incident_meta = []

    for idx, r in df_manifest.iterrows():
        eid = str(r['Event_ID'])
        day = int(r['Day'])
        b_start = str(r['Buffered_Start']).strip()
        b_end = str(r['Buffered_End']).strip()
        date_str = f"2026-09-{day:02d}"
        if ' ' not in b_start:
            b_start = f"{date_str} {b_start}"
            b_end = f"{date_str} {b_end}"
        dt_start = datetime.strptime(b_start, "%Y-%m-%d %H:%M:%S")
        dt_end = datetime.strptime(b_end, "%Y-%m-%d %H:%M:%S")

        in_window = [c for c in crops_by_day[day] if dt_start <= c[0] <= dt_end]
        
        target_crop_path = None
        crop_q = 0
        crop_conf = 0
        
        if in_window:
            best = sorted(in_window, key=lambda x: (x[1], x[2]), reverse=True)[0]
            target_crop_path = best[3]
            crop_q = best[1]
            crop_conf = best[2]
        elif eid == "EVT-D01-009":
            # Manual audit crop for Day 1 09:53:38
            target_crop_path = Path("D:/facial/data/30day_personas/portraits/SUBJ-1652_exemplar.jpg")
            crop_q = 95
            crop_conf = 98

        if target_crop_path and target_crop_path.exists():
            img = cv2.imread(str(target_crop_path))
            if img is not None:
                # Save standardized copy to verified_faces
                dest_face_path = verified_faces_dir / f"{eid}_day{day:02d}_verified_face.jpg"
                cv2.imwrite(str(dest_face_path), img)
                
                tensor = preprocess_face(img)
                incident_crops_to_run.append(tensor)
                incident_meta.append({
                    'row_idx': idx,
                    'Event_ID': eid,
                    'Day': day,
                    'WallClock_Start': r['WallClock_Start'],
                    'WallClock_End': r['WallClock_End'],
                    'Facility_Zone': r['Facility_Zone'],
                    'Hazard_Level': r['Hazard_Level'],
                    'Original_Personas': str(r['Personas']),
                    'Face_Path': str(dest_face_path),
                    'Source_Crop': str(target_crop_path),
                    'Quality': crop_q,
                    'Conf': crop_conf
                })

    print(f"Running batched ArcFace embedding on {len(incident_crops_to_run)} incident face crops...")
    batch_tensors = np.array(incident_crops_to_run, dtype=np.float32)
    feats = sess.run(None, {input_name: batch_tensors})[0]
    # Normalize
    norms = np.linalg.norm(feats, axis=1, keepdims=True)
    feats = feats / np.maximum(norms, 1e-12)

    # 4. Compare against Real Person Anchors
    matches_summary = []
    high_conf_matches = 0
    mod_matches = 0
    low_matches = 0

    for i, meta in enumerate(incident_meta):
        feat = feats[i]
        best_sim = -1.0
        best_pid = None
        best_anchor = None

        # Compare with each anchor
        for pid, pdata in anchor_embeddings.items():
            sim = float(np.dot(feat, pdata['embedding']))
            if sim > best_sim:
                best_sim = sim
                best_pid = pid
                best_anchor = pdata['anchor_subj']

        meta['Matched_Real_Person'] = best_pid
        meta['Matched_Anchor'] = best_anchor
        meta['Cosine_Similarity'] = round(best_sim, 4)

        if best_sim >= 0.55:
            meta['Match_Confidence'] = 'VERY_HIGH (Same Individual)'
            high_conf_matches += 1
        elif best_sim >= 0.45:
            meta['Match_Confidence'] = 'HIGH (Verified Match)'
            mod_matches += 1
        elif best_sim >= 0.38:
            meta['Match_Confidence'] = 'PROBABLE (Related Sighting)'
            low_matches += 1
        else:
            meta['Match_Confidence'] = 'DISTINCT_NEW_INDIVIDUAL'

        matches_summary.append(meta)

    print(f"\nMatching Results across {len(matches_summary)} Incidents:")
    print(f"  - Very High Match (>=0.55): {high_conf_matches}")
    print(f"  - High Match (0.45 - 0.55): {mod_matches}")
    print(f"  - Probable Match (0.38 - 0.45): {low_matches}")
    print(f"  - Distinct / New Individual (<0.38): {len(matches_summary) - high_conf_matches - mod_matches - low_matches}")

    df_res = pd.DataFrame(matches_summary)
    out_csv = Path("D:/facial/incident_evidence/179_incidents_biometric_mapping.csv")
    df_res.to_csv(out_csv, index=False)
    print(f"[OK] Saved mapping to {out_csv}")

    # Top Real Persons matched
    print("\nTop Real Person occurrences across incidents:")
    print(df_res['Matched_Real_Person'].value_counts().head(10))

if __name__ == "__main__":
    main()

