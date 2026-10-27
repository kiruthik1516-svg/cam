import cv2
import numpy as np
import insightface
from insightface.app import FaceAnalysis
from pathlib import Path
import json

app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
app.prepare(ctx_id=0, det_size=(320, 320))
rec_model = app.models['recognition']

# 1. User Face Feature
user_path = Path("C:/Users/mkiru/.gemini/antigravity/brain/8c6e85a2-8ea1-4c6c-bb23-a9aed5b45fc6/.user_uploaded/media_1793097377094_15804899.png")
user_img = cv2.imread(str(user_path))

# Use FaceAnalysis to get properly aligned face crop if possible
h, w = user_img.shape[:2]
user_pad = cv2.copyMakeBorder(user_img, h//2, h//2, w//2, w//2, cv2.BORDER_CONSTANT, value=[0,0,0])
user_scaled = cv2.resize(user_pad, (0,0), fx=2.0, fy=2.0)
faces = app.get(user_scaled)

if faces:
    user_feat = faces[0].embedding
    user_feat = user_feat / np.linalg.norm(user_feat)
    print("Extracted aligned user face embedding.")
else:
    user_112 = cv2.resize(user_img, (112, 112))
    user_feat = rec_model.get_feat(user_112).flatten()
    user_feat = user_feat / np.linalg.norm(user_feat)
    print("Used resized user image embedding.")

# 2. Load all 1651 exemplars
port_dir = Path("D:/facial/data/30day_personas/portraits")
exemplars = sorted(list(port_dir.glob("SUBJ-*_exemplar.jpg")))
print(f"Loaded {len(exemplars)} exemplar portraits.")

# Batch feature extraction
scores = []
for f in exemplars:
    im = cv2.imread(str(f))
    if im is None: continue
    im_112 = cv2.resize(im, (112, 112))
    feat = rec_model.get_feat(im_112).flatten()
    norm = np.linalg.norm(feat)
    if norm > 1e-6:
        feat = feat / norm
        sim = float(np.dot(user_feat, feat))
        subj_id = f.stem.replace("_exemplar", "")
        scores.append((subj_id, sim, f.name))

scores.sort(key=lambda x: x[1], reverse=True)

print("\n" + "="*60)
print("TOP 20 BEST MATCHES ACROSS ALL 1,651 30-DAY PERSONAS")
print("="*60)
for subj_id, sim, fname in scores[:20]:
    match_tag = " >>> POTENTIAL MATCH <<<" if sim > 0.40 else ""
    print(f"  {subj_id:<12}: Cosine Similarity = {sim:.4f} ({fname}){match_tag}")

print("\n" + "="*60)
print("SPECIFIC PRIMARY SUBJECTS COMPARISON")
print("="*60)
subj_dict = {s[0]: s[1] for s in scores}
for s in ["SUBJ-01", "SUBJ-02", "SUBJ-03", "SUBJ-04", "SUBJ-05", "SUBJ-06", "SUBJ-07", "SUBJ-08", "SUBJ-09", "SUBJ-10"]:
    if s in subj_dict:
        print(f"  {s:<12}: Cosine Similarity = {subj_dict[s]:.4f}")

# Save full ranking to json
with open("D:/facial/user_face_matching_scores.json", "w") as out_f:
    json.dump([{"subject": s[0], "similarity": round(s[1], 4), "file": s[2]} for s in scores], out_f, indent=2)
print("\nFull ranking saved to D:/facial/user_face_matching_scores.json")

