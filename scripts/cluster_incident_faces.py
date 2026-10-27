import cv2
import numpy as np
import pandas as pd
from pathlib import Path
import onnxruntime as ort

def get_arcface_session():
    model_path = Path("C:/Users/mkiru/.insightface/models/buffalo_l/w600k_r50.onnx")
    opts = ort.SessionOptions()
    opts.intra_op_num_threads = 6
    return ort.InferenceSession(str(model_path), opts, providers=['CPUExecutionProvider'])

def preprocess_face(img):
    img = cv2.resize(img, (112, 112))
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = np.transpose(img, (2, 0, 1)).astype(np.float32)
    img = (img - 127.5) / 127.5
    return img

def main():
    sess = get_arcface_session()
    input_name = sess.get_inputs()[0].name
    
    df = pd.read_csv("D:/facial/incident_evidence/179_incidents_biometric_mapping.csv")
    tensors = []
    valid_indices = []

    for i, r in df.iterrows():
        p = Path(r['Face_Path'])
        if p.exists():
            img = cv2.imread(str(p))
            if img is not None:
                tensors.append(preprocess_face(img))
                valid_indices.append(i)

    print(f"Loaded {len(tensors)} valid face images.")
    batch = np.array(tensors, dtype=np.float32)
    feats = sess.run(None, {input_name: batch})[0]
    norms = np.linalg.norm(feats, axis=1, keepdims=True)
    feats = feats / np.maximum(norms, 1e-12)

    # Compute 179 x 179 cosine similarity matrix
    sim_mat = np.dot(feats, feats.T)

    # Let's inspect the 20 low similarity incidents (< 0.38 to anchors)
    low_idx_in_batch = [i for i, idx in enumerate(valid_indices) if df.iloc[idx]['Cosine_Similarity'] < 0.38]
    print(f"\nAnalyzing 20 low similarity incidents among themselves:")
    pairs_found = []
    for i in range(len(low_idx_in_batch)):
        for j in range(i + 1, len(low_idx_in_batch)):
            idx_a = low_idx_in_batch[i]
            idx_b = low_idx_in_batch[j]
            s = sim_mat[idx_a, idx_b]
            if s >= 0.45:
                row_a = df.iloc[valid_indices[idx_a]]
                row_b = df.iloc[valid_indices[idx_b]]
                pairs_found.append((row_a['Event_ID'], row_b['Event_ID'], s, row_a['Day'], row_b['Day']))

    print(f"Found {len(pairs_found)} high similarity pairs among the 20 'new' incidents:")
    for p in pairs_found:
        print(f"  {p[0]} (Day {p[3]}) <-> {p[1]} (Day {p[4]}): sim={p[2]:.4f}")

if __name__ == "__main__":
    main()
