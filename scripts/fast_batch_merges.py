import json
import os
import cv2
import numpy as np
import onnxruntime as ort
from pathlib import Path

# Load ONNX ArcFace model with 4 threads
opts = ort.SessionOptions()
opts.intra_op_num_threads = 4
rec_model_path = r'C:\Users\mkiru\.insightface\models\buffalo_l\w600k_r50.onnx'
session = ort.InferenceSession(rec_model_path, opts, providers=['CPUExecutionProvider'])

# Load personas
with open("D:/facial/data/30day_personas/30day_personas_master.json", "r", encoding="utf-8") as f:
    master = json.load(f)

personas = master["personas"]
# Get top 50 + all 18 contacts
top_p = personas[:50]
contacts = [p for p in personas if p["zone_direct_contacts"] > 0]

eval_p = {}
for p in top_p + contacts:
    eval_p[p["persona_id"]] = p

pids = []
imgs = []

for pid in eval_p:
    p_path = Path(f"D:/facial/data/30day_personas/portraits/{pid}_exemplar.jpg")
    if p_path.exists():
        im = cv2.imread(str(p_path))
        if im is not None:
            im = cv2.resize(im, (112, 112))
            im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
            im = np.transpose(im, (2, 0, 1)).astype(np.float32)
            im = (im - 127.5) / 127.5
            imgs.append(im)
            pids.append(pid)

print(f"Loaded {len(imgs)} valid persona portraits for batch inference...", flush=True)

# Batch inference
batch = np.array(imgs, dtype=np.float32)
input_name = session.get_inputs()[0].name
features = session.run(None, {input_name: batch})[0]

# Normalize features
norms = np.linalg.norm(features, axis=1, keepdims=True)
norms[norms == 0] = 1.0
features = features / norms

print(f"Computed normalized feature matrix: {features.shape}", flush=True)

# Compute full cosine similarity matrix: (N, N)
sim_matrix = np.dot(features, features.T)

# Find high-similarity pairs (>= 0.38)
matches = []
for i in range(len(pids)):
    for j in range(i + 1, len(pids)):
        sim = float(sim_matrix[i, j])
        if sim >= 0.38:
            matches.append((sim, pids[i], pids[j]))

matches.sort(reverse=True)
print(f"\n=== CANDIDATE PERSONA MERGES (Cosine Sim >= 0.38) ===", flush=True)
print(f"Total pairs found: {len(matches)}", flush=True)
for sim, p1, p2 in matches:
    p1_dets = eval_p[p1]["total_detections"]
    p2_dets = eval_p[p2]["total_detections"]
    p1_contacts = eval_p[p1]["zone_direct_contacts"]
    p2_contacts = eval_p[p2]["zone_direct_contacts"]
    print(f"  {p1} ({p1_dets} dets, {p1_contacts} contacts) <==> {p2} ({p2_dets} dets, {p2_contacts} contacts) | Sim = {sim:.4f}", flush=True)
