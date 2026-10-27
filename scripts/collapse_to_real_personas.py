import json
import os
import cv2
import numpy as np
import onnxruntime as ort
import networkx as nx
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

# Batch inference
batch = np.array(imgs, dtype=np.float32)
input_name = session.get_inputs()[0].name
features = session.run(None, {input_name: batch})[0]

# Normalize features
norms = np.linalg.norm(features, axis=1, keepdims=True)
norms[norms == 0] = 1.0
features = features / norms

# Compute full cosine similarity matrix: (N, N)
sim_matrix = np.dot(features, features.T)

# Build graph with threshold >= 0.55 (strict high-confidence identity threshold)
G = nx.Graph()
for pid in pids:
    G.add_node(pid)

threshold = 0.55
for i in range(len(pids)):
    for j in range(i + 1, len(pids)):
        sim = float(sim_matrix[i, j])
        if sim >= threshold:
            G.add_edge(pids[i], pids[j], weight=sim)

components = list(nx.connected_components(G))
components.sort(key=len, reverse=True)

print(f"\n=======================================================", flush=True)
print(f"COLLAPSE RESULT: {len(pids)} personas collapsed into {len(components)} REAL INDIVIDUALS", flush=True)
print(f"=======================================================\n", flush=True)

real_personas_manifest = []

for idx, comp in enumerate(components, start=1):
    comp_list = sorted(list(comp), key=lambda x: eval_p[x]["total_detections"], reverse=True)
    anchor_id = comp_list[0]
    tot_dets = sum(eval_p[x]["total_detections"] for x in comp_list)
    tot_contacts = sum(eval_p[x]["zone_direct_contacts"] for x in comp_list)
    all_days = set()
    for x in comp_list:
        all_days.update(eval_p[x].get("active_days", []))
    
    print(f"REAL PERSON #{idx:02d} [Anchor: {anchor_id}]", flush=True)
    print(f"  Includes {len(comp_list)} DBSCAN fragments: {', '.join(comp_list)}", flush=True)
    print(f"  Total Detections: {tot_dets:,} | Active Days: {len(all_days)} | Equipment Contacts: {tot_contacts}", flush=True)
    print("", flush=True)

    real_personas_manifest.append({
        "Real_Person_ID": f"REAL-{idx:02d}",
        "Anchor_Persona": anchor_id,
        "Fragmented_Personas": comp_list,
        "Total_Detections": tot_dets,
        "Active_Days_Count": len(all_days),
        "Total_Equipment_Contacts": tot_contacts,
        "Anchor_Portrait": f"data/30day_personas/portraits/{anchor_id}_exemplar.jpg"
    })

out_json = Path("D:/facial/data/30day_personas/consolidated_real_personas.json")
with open(out_json, "w", encoding="utf-8") as f:
    json.dump(real_personas_manifest, f, indent=2)

print(f"[OK] Saved consolidated real personas manifest: {out_json}", flush=True)

