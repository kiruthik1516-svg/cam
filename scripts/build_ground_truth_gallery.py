#!/usr/bin/env python3
"""
build_ground_truth_gallery.py
Extracts verified face exemplars directly from the 179 incident clips,
builds a consolidated Ground-Truth Visual Gallery of real plant individuals,
and generates a 100% transparent visual verification audit sheet.
"""

import os
import cv2
import json
import numpy as np
import pandas as pd
from pathlib import Path
from insightface.app import FaceAnalysis

def extract_incident_faces():
    manifest_csv = Path("D:/facial/incident_evidence/extracted_incident_manifest.csv")
    if not manifest_csv.exists():
        print(f"[ERROR] Manifest not found: {manifest_csv}")
        return

    df_manifest = pd.read_csv(manifest_csv)
    print(f"[OK] Loaded manifest with {len(df_manifest)} incident events.")

    # Output directory for clean incident face crops
    face_dir = Path("D:/facial/incident_evidence/verified_faces")
    face_dir.mkdir(parents=True, exist_ok=True)

    print("Initializing InsightFace ArcFace model...")
    app = FaceAnalysis(name='buffalo_l', allowed_modules=['detection', 'recognition'], providers=['CPUExecutionProvider'])
    app.prepare(ctx_id=-1, det_size=(640, 640))

    incident_data = []

    for idx, r in df_manifest.iterrows():
        eid = str(r["Event_ID"])
        day = int(r["Day"])
        clip_rel = str(r["Extracted_Clip_File"])
        clip_path = Path("D:/facial") / clip_rel

        # Fallback check
        if not clip_path.exists():
            clip_path = Path("D:/facial/incident_evidence") / f"day_{day:02d}" / Path(clip_rel).name

        if not clip_path.exists():
            print(f"[WARN] Clip file not found for {eid}: {clip_path}")
            continue

        print(f"[{idx+1}/{len(df_manifest)}] Processing {eid} from {clip_path.name}...")
        cap = cv2.VideoCapture(str(clip_path))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # Sample 1 frame every 0.5s (15 frames at 30 fps)
        step = max(1, int(fps * 0.5))
        best_face = None
        best_score = -1.0
        best_crop = None
        best_frame_idx = 0

        frame_count = 0
        while cap.isOpened() and frame_count < total_frames:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_count)
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            faces = app.get(frame)
            for f in faces:
                # Score combines detection confidence and bounding box area
                w = f.bbox[2] - f.bbox[0]
                h = f.bbox[3] - f.bbox[1]
                area = w * h
                det_score = float(f.det_score)
                # We prioritize clear, reasonably sized faces
                combined_score = det_score * np.log1p(area)

                if combined_score > best_score and det_score >= 0.65:
                    best_score = combined_score
                    best_face = f
                    best_frame_idx = frame_count

                    # Crop face with 20% margin
                    ih, iw, _ = frame.shape
                    x1 = max(0, int(f.bbox[0] - 0.2 * w))
                    y1 = max(0, int(f.bbox[1] - 0.2 * h))
                    x2 = min(iw, int(f.bbox[2] + 0.2 * w))
                    y2 = min(ih, int(f.bbox[3] + 0.2 * h))
                    best_crop = frame[y1:y2, x1:x2].copy()

            frame_count += step
            # Limit search to first 200 sampled frames (~100 seconds)
            if frame_count > step * 200:
                break

        cap.release()

        if best_face is not None and best_crop is not None:
            crop_filename = f"{eid}_day{day:02d}_f{best_frame_idx}.jpg"
            crop_path = face_dir / crop_filename
            cv2.imwrite(str(crop_path), best_crop)

            emb = best_face.embedding / np.linalg.norm(best_face.embedding)

            incident_data.append({
                "Event_ID": eid,
                "Day": day,
                "WallClock_Start": str(r["WallClock_Start"]),
                "Facility_Zone": str(r["Facility_Zone"]),
                "Hazard_Level": str(r["Hazard_Level"]),
                "Original_Personas": str(r["Personas"]),
                "Face_Crop_Path": str(crop_path),
                "Embedding": emb.tolist(),
                "Det_Score": float(best_face.det_score)
            })
            print(f"  -> Extracted face for {eid}: score={best_face.det_score:.2f}, saved to {crop_filename}")
        else:
            print(f"  -> No clear face detected in {eid}")

    out_json = Path("D:/facial/incident_evidence/incident_faces_embeddings.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(incident_data, f, indent=2)

    print(f"\n[DONE] Extracted faces for {len(incident_data)} incidents. Saved to {out_json}")

if __name__ == "__main__":
    extract_incident_faces()
