import json
import glob
import os
import cv2
import numpy as np
import onnxruntime as ort
from pathlib import Path

rec_model_path = r'C:\Users\mkiru\.insightface\models\buffalo_l\w600k_r50.onnx'
session = ort.InferenceSession(rec_model_path, providers=['CPUExecutionProvider'])

def get_embedding(img_path):
    img = cv2.imread(str(img_path))
    if img is None:
        return None
    img = cv2.resize(img, (112, 112))
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = np.transpose(img, (2, 0, 1)).astype(np.float32)
    img = (img - 127.5) / 127.5
    img = np.expand_dims(img, axis=0)
    feat = session.run(None, {session.get_inputs()[0].name: img})[0][0]
    return feat / np.linalg.norm(feat)

# Load master personas
with open("D:/facial/data/30day_personas/30day_personas_master.json", "r", encoding="utf-8") as f:
    master = json.load(f)

personas = master["personas"]
# Get top 30 personas + all 18 contact personas
top_personas = personas[:30]
contacts = [p for p in personas if p["zone_direct_contacts"] > 0]

eval_personas = {}
for p in top_personas + contacts:
    eval_personas[p["persona_id"]] = p

print(f"Total distinct personas to evaluate: {len(eval_personas)}")

embeddings = {}
for pid in eval_personas:
    path = Path(f"D:/facial/data/30day_personas/portraits/{pid}_exemplar.jpg")
    if path.exists():
        emb = get_embedding(path)
        if emb is not None:
            embeddings[pid] = emb

print(f"Extracted embeddings for {len(embeddings)} personas.")

# Pairwise similarity
pids = sorted(embeddings.keys())
matches = []
for i in range(len(pids)):
    for j in range(i + 1, len(pids)):
        p1, p2 = pids[i], pids[j]
        sim = float(np.dot(embeddings[p1], embeddings[p2]))
        if sim >= 0.40:
            matches.append((sim, p1, p2))

matches.sort(reverse=True)
print(f"\n=== MATCHES >= 0.40 ({len(matches)} pairs) ===")
for sim, p1, p2 in matches:
    print(f"  {p1} <--> {p2} : Cosine Sim = {sim:.4f}")

