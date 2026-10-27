import json
import glob
import os
import cv2
import numpy as np
from pathlib import Path
from insightface.app import FaceAnalysis

print("Initializing InsightFace...")
app = FaceAnalysis(name='buffalo_l', allowed_modules=['detection', 'recognition'], providers=['CPUExecutionProvider'])
app.prepare(ctx_id=-1, det_size=(640, 640))

# Load master personas
with open("D:/facial/data/30day_personas/30day_personas_master.json", "r", encoding="utf-8") as f:
    master = json.load(f)

personas = master["personas"]
# Get top 20 + all 18 contact personas
top_personas = personas[:20]
contacts = [p for p in personas if p["zone_direct_contacts"] > 0]

eval_personas = {}
for p in top_personas + contacts:
    eval_personas[p["persona_id"]] = p

print(f"Total distinct personas to evaluate: {len(eval_personas)}")

# Extract embeddings for each exemplar
embeddings = {}
for pid, pdata in eval_personas.items():
    port_file = pdata.get("exemplar_portrait_file", "")
    full_path = Path("D:/facial/data") / port_file
    if not full_path.exists():
        full_path = Path("D:/facial/data/30day_personas/portraits") / f"{pid}_exemplar.jpg"
    
    if full_path.exists():
        img = cv2.imread(str(full_path))
        if img is not None:
            faces = app.get(img)
            if faces:
                emb = faces[0].embedding
                emb = emb / np.linalg.norm(emb)
                embeddings[pid] = emb
            else:
                print(f"[WARN] No face detected in exemplar for {pid}")
        else:
            print(f"[WARN] Could not read {full_path}")
    else:
        print(f"[WARN] Path not found: {full_path}")

print(f"Successfully extracted embeddings for {len(embeddings)} personas.")

# Check pairwise similarities
print("\n=== HIGH SIMILARITY PAIRS (Cosine Similarity >= 0.40) ===")
pids = sorted(embeddings.keys())
matches = []
for i in range(len(pids)):
    for j in range(i + 1, len(pids)):
        p1, p2 = pids[i], pids[j]
        sim = float(np.dot(embeddings[p1], embeddings[p2]))
        if sim >= 0.40:
            matches.append((sim, p1, p2))

matches.sort(reverse=True)
for sim, p1, p2 in matches:
    print(f"  {p1} <--> {p2} : Cosine Sim = {sim:.4f}")

if not matches:
    print("  No pairs found above 0.40 threshold.")
