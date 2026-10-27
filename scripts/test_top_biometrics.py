import cv2
import numpy as np
import insightface
from insightface.app import FaceAnalysis
from pathlib import Path

# Init InsightFace
app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
app.prepare(ctx_id=0, det_size=(320, 320))

def get_emb(img):
    if img is None: return None
    h, w = img.shape[:2]
    # Pad
    padded = cv2.copyMakeBorder(img, h//2, h//2, w//2, w//2, cv2.BORDER_CONSTANT, value=[0,0,0])
    scaled = cv2.resize(padded, (0,0), fx=2.0, fy=2.0)
    faces = app.get(scaled)
    if not faces:
        faces = app.get(img)
    if faces:
        emb = faces[0].embedding
        return emb / np.linalg.norm(emb)
    return None

# 1. User Face
user_path = Path("C:/Users/mkiru/.gemini/antigravity/brain/8c6e85a2-8ea1-4c6c-bb23-a9aed5b45fc6/.user_uploaded/media_1793097377094_15804899.png")
user_emb = get_emb(cv2.imread(str(user_path)))
print(f"User image embedding: {'OK' if user_emb is not None else 'FAILED'}")

# 2. 09:53:38 Frame Operator
frame_path = Path("D:/facial/incident_evidence/day_01/verify_095338_extracted.jpg")
frame = cv2.imread(str(frame_path))
op_crop = frame[320:800, 1100:1400] if frame is not None else None
clip_emb = get_emb(op_crop)
print(f"09:53:38 operator crop embedding: {'OK' if clip_emb is not None else 'FAILED'}")

target_emb = user_emb if user_emb is not None else clip_emb

# 3. Test Day 1 Identities (per-01 to per-07)
print("\n--- Matching against Day 1 Personas (day1_identities) ---")
ident_dir = Path("D:/facial/data/day1_identities")
for f in sorted(ident_dir.glob("per-*.jpg")):
    emb = get_emb(cv2.imread(str(f)))
    if emb is not None:
        sim_user = float(np.dot(user_emb, emb)) if user_emb is not None else 0.0
        sim_clip = float(np.dot(clip_emb, emb)) if clip_emb is not None else 0.0
        print(f"  {f.name:<38} | Sim(User): {sim_user:.4f} | Sim(Clip): {sim_clip:.4f}")

# 4. Test Top 25 30-Day Personas (SUBJ-01 to SUBJ-25)
print("\n--- Matching against Top 25 30-Day Exemplar Personas ---")
port_dir = Path("D:/facial/data/30day_personas/portraits")
for i in range(1, 26):
    f = port_dir / f"SUBJ-{i:02d}_exemplar.jpg"
    if f.exists():
        emb = get_emb(cv2.imread(str(f)))
        if emb is not None:
            sim_user = float(np.dot(user_emb, emb)) if user_emb is not None else 0.0
            sim_clip = float(np.dot(clip_emb, emb)) if clip_emb is not None else 0.0
            is_match = " *** MATCH! ***" if sim_user > 0.40 else ""
            print(f"  SUBJ-{i:02d}_exemplar.jpg {'':<16} | Sim(User): {sim_user:.4f} | Sim(Clip): {sim_clip:.4f}{is_match}")

