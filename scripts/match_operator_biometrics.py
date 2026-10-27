import cv2
import numpy as np
import insightface
from insightface.app import FaceAnalysis
from pathlib import Path
import json

# Initialize InsightFace
app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
app.prepare(ctx_id=0, det_size=(640, 640))

# Load user attached image
user_img_path = Path("C:/Users/mkiru/.gemini/antigravity/brain/8c6e85a2-8ea1-4c6c-bb23-a9aed5b45fc6/.user_uploaded/media_1793097377094_15804899.png")
user_img = cv2.imread(str(user_img_path))

# If user_img is already a tight crop, InsightFace detector might need padding
h, w = user_img.shape[:2]
user_padded = cv2.copyMakeBorder(user_img, h//2, h//2, w//2, w//2, cv2.BORDER_CONSTANT, value=[0,0,0])

user_faces = app.get(user_padded)
print(f"User image faces detected: {len(user_faces)}")

if len(user_faces) == 0:
    # Try with original or scale up
    user_scaled = cv2.resize(user_padded, (0,0), fx=2.0, fy=2.0)
    user_faces = app.get(user_scaled)
    print(f"User scaled faces detected: {len(user_faces)}")

user_emb = None
if len(user_faces) > 0:
    user_emb = user_faces[0].embedding
    user_emb = user_emb / np.linalg.norm(user_emb)
    print("User face embedding extracted successfully (512-D).")

# Also extract face directly from Day 1 09:53:38 frame:
day1_frame_path = Path("D:/facial/incident_evidence/day_01/verify_095338_extracted.jpg")
day1_frame = cv2.imread(str(day1_frame_path))
clip_faces = []
if day1_frame is not None:
    # Operator is at X=1100..1400, Y=300..800
    op_crop = day1_frame[300:800, 1100:1400]
    clip_faces = app.get(op_crop)
    print(f"Faces in 09:53:38 operator crop: {len(clip_faces)}")
    if len(clip_faces) == 0:
        # scale up operator crop
        op_scaled = cv2.resize(op_crop, (0,0), fx=2.0, fy=2.0)
        clip_faces = app.get(op_scaled)
        print(f"Faces in 09:53:38 scaled crop: {len(clip_faces)}")

clip_emb = None
if len(clip_faces) > 0:
    clip_emb = clip_faces[0].embedding
    clip_emb = clip_emb / np.linalg.norm(clip_emb)
    print("09:53:38 clip face embedding extracted successfully.")

target_emb = user_emb if user_emb is not None else clip_emb

# Now compare target_emb against all exemplar portraits in 30day_personas
port_dir = Path("D:/facial/data/30day_personas/portraits")
exemplars = list(port_dir.glob("SUBJ-*_exemplar.jpg"))
print(f"Testing against {len(exemplars)} exemplar portraits...")

results = []
for p in exemplars:
    im = cv2.imread(str(p))
    if im is None: continue
    # Pad exemplar for detection
    ph, pw = im.shape[:2]
    im_pad = cv2.copyMakeBorder(im, ph//2, ph//2, pw//2, pw//2, cv2.BORDER_CONSTANT, value=[0,0,0])
    im_scaled = cv2.resize(im_pad, (0,0), fx=2.0, fy=2.0)
    faces = app.get(im_scaled)
    if len(faces) > 0:
        emb = faces[0].embedding
        emb = emb / np.linalg.norm(emb)
        if target_emb is not None:
            sim = float(np.dot(target_emb, emb))
            results.append((p.stem, sim, p.name))

results.sort(key=lambda x: x[1], reverse=True)
print("\n--- TOP 15 BIOMETRIC MATCHES (Cosine Similarity) ---")
for subj, sim, fname in results[:15]:
    print(f"  {subj:<20}: Cosine Similarity = {sim:.4f} ({fname})")

# Check specifically SUBJ-01, SUBJ-02, SUBJ-03, SUBJ-04
print("\n--- SPECIFIC PERSONA COMPARISONS ---")
for subj, sim, fname in results:
    if subj in ["SUBJ-01_exemplar", "SUBJ-02_exemplar", "SUBJ-03_exemplar", "SUBJ-04_exemplar", "SUBJ-07_exemplar"]:
        print(f"  {subj:<20}: Cosine Similarity = {sim:.4f}")

