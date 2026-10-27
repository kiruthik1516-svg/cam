import cv2
import numpy as np
import insightface
from insightface.app import FaceAnalysis
from pathlib import Path

app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
app.prepare(ctx_id=0, det_size=(320, 320))

def get_emb(img):
    if img is None: return None
    h, w = img.shape[:2]
    padded = cv2.copyMakeBorder(img, h//2, h//2, w//2, w//2, cv2.BORDER_CONSTANT, value=[0,0,0])
    scaled = cv2.resize(padded, (0,0), fx=2.0, fy=2.0)
    faces = app.get(scaled)
    if not faces: faces = app.get(img)
    if faces:
        emb = faces[0].embedding
        return emb / np.linalg.norm(emb)
    return None

user_path = Path("C:/Users/mkiru/.gemini/antigravity/brain/8c6e85a2-8ea1-4c6c-bb23-a9aed5b45fc6/.user_uploaded/media_1793097377094_15804899.png")
user_emb = get_emb(cv2.imread(str(user_path)))

crop_dir = Path("D:/facial/data/day01_all_face_crops")
all_files = sorted(list(crop_dir.glob("*.jpg")))
print(f"Total face crops on Day 1: {len(all_files)}")

# Check crops in morning hours (08:30 to 10:30)
morning_files = [f for f in all_files if any(k in f.name for k in ['_09-', '_08-', '_10-'])]
print(f"Morning face crops (08:00 - 10:59): {len(morning_files)}")

matches = []
for idx, f in enumerate(morning_files):
    emb = get_emb(cv2.imread(str(f)))
    if emb is not None:
        sim = float(np.dot(user_emb, emb))
        if sim > 0.35:
            matches.append((f.name, sim))
            print(f"  [MATCH] {f.name}: Sim = {sim:.4f}")

matches.sort(key=lambda x: x[1], reverse=True)
print(f"\nTotal matches > 0.35: {len(matches)}")
for name, sc in matches[:20]:
    print(f"  {name}: {sc:.4f}")

