#!/usr/bin/env python3
import cv2
import glob
import json
import os
import numpy as np
from insightface.app import FaceAnalysis

def main():
    app = FaceAnalysis(name='buffalo_l', allowed_modules=['detection', 'recognition'], providers=['CPUExecutionProvider'])
    app.prepare(ctx_id=-1, det_size=(640, 640))

    # 1. Detect face on the 09:53:38 frame or candidate frame
    cand_path = r'D:\facial\data\stage1_candidates\day_01\day01_56_8_DBGT_IPC56_f53eeb62d1134483a5b6599e31dce8f6_20260901094423_w03_00006.jpg'
    cand = cv2.imread(cand_path)
    faces = app.get(cand)
    if not faces:
        print("No face detected in candidate frame.")
        return

    target_emb = faces[0].embedding
    target_emb = target_emb / np.linalg.norm(target_emb)
    print(f"[OK] Extracted target face embedding at 09:53 (det_score: {faces[0].det_score:.2f})")

    # 2. Compare against all 1,651 persona exemplars
    portraits = sorted(glob.glob(r'D:\facial\data\30day_personas\portraits\SUBJ-*_exemplar.jpg'))
    print(f"Comparing against {len(portraits)} master persona exemplars...")

    scores = []
    for p in portraits:
        p_img = cv2.imread(p)
        if p_img is None:
            continue
        p_faces = app.get(p_img)
        if p_faces:
            p_emb = p_faces[0].embedding
            p_emb = p_emb / np.linalg.norm(p_emb)
            sim = float(np.dot(target_emb, p_emb))
            pid = os.path.basename(p).split('_')[0]
            scores.append((pid, sim))

    scores.sort(key=lambda x: x[1], reverse=True)
    print("\n=== TOP MATCHING PERSONAS ===")
    for pid, s in scores[:10]:
        print(f"  {pid}: Cosine Similarity = {s:.4f}")

    best_pid = scores[0][0]
    best_sim = scores[0][1]
    print(f"\n[BEST MATCH] -> {best_pid} (Score: {best_sim:.4f})")

    # 3. Pull all encounter days and times for this persona from 30day_personas_master.json
    with open(r'D:\facial\data\30day_personas\30day_personas_master.json', 'r', encoding='utf-8') as f:
        master = json.load(f)

    matched_persona = None
    for p in master['personas']:
        if p['persona_id'] == best_pid:
            matched_persona = p
            break

    if matched_persona:
        print(f"\n=== ENCOUNTER TIMELINE FOR {best_pid} ===")
        print(f"Total Detections: {matched_persona['total_detections']}")
        print(f"Days Active Count: {matched_persona['days_active_count']} days")
        print(f"Active Calendar Days: {matched_persona['active_days']}")
        print(f"First Seen: {matched_persona['first_seen']}")
        print(f"Last Seen:  {matched_persona['last_seen']}")
        print(f"Shift Distribution: {matched_persona.get('shift_distribution')}")
        print(f"Critical Zone Interactions: {len(matched_persona.get('zone_events_log', []))}")
        print("\nZone Events:")
        for ev in matched_persona.get('zone_events_log', []):
            print(f"  - {ev['timestamp']} | {ev['zone_name']} ({ev['hazard_level']}) | Direct Contact: {ev.get('is_direct_contact', False)}")

if __name__ == '__main__':
    main()

