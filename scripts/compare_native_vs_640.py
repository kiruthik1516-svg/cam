import time
from pathlib import Path
import cv2
import numpy as np
from insightface.app import FaceAnalysis

def run_comparison(sample_dir="/app/data/stage1_candidates/day_01", num_samples=30):
    images = sorted(list(Path(sample_dir).glob("*.jpg")))[:num_samples]
    if not images:
        print(f"No images found in {sample_dir}")
        return

    print(f"\n========================================================================")
    print(f"SCIENTIFIC VERIFICATION: NATIVE (1280x800) VS CALIBRATED (640x640)")
    print(f"Sample Size: {len(images)} real CCTV interaction frames from camera IPC56")
    print(f"========================================================================\n")

    # Load 1280x800 model
    print("Loading InsightFace buffalo_l with det_size=(1280, 800)...")
    app_native = FaceAnalysis(
        name="buffalo_l",
        allowed_modules=["detection", "recognition"],
        providers=["CPUExecutionProvider"],
    )
    app_native.prepare(ctx_id=-1, det_size=(1280, 800))

    # Load 640x640 model
    print("Loading InsightFace buffalo_l with det_size=(640, 640)...")
    app_640 = FaceAnalysis(
        name="buffalo_l",
        allowed_modules=["detection", "recognition"],
        providers=["CPUExecutionProvider"],
    )
    app_640.prepare(ctx_id=-1, det_size=(640, 640))

    # 1. Benchmark Native
    print("\n[1/2] Benchmarking Native (1280x800)...")
    t0 = time.time()
    faces_native = []
    for p in images:
        img = cv2.imread(str(p))
        f = app_native.get(img)
        faces_native.append(f)
    t_native = time.time() - t0
    fps_native = len(images) / t_native

    # 2. Benchmark 640
    print("[2/2] Benchmarking Calibrated 640x640...")
    t0 = time.time()
    faces_640 = []
    for p in images:
        img = cv2.imread(str(p))
        f = app_640.get(img)
        faces_640.append(f)
    t_640 = time.time() - t0
    fps_640 = len(images) / t_640

    # 3. Analyze Accuracy & Vector Similarity
    total_faces_native = sum(len(f) for f in faces_native)
    total_faces_640 = sum(len(f) for f in faces_640)

    cosine_similarities = []
    ious = []

    for fn_list, f6_list in zip(faces_native, faces_640):
        if not fn_list or not f6_list:
            continue
        for fn in fn_list:
            b1 = fn.bbox
            v1 = fn.normed_embedding
            best_iou = 0.0
            best_sim = 0.0
            for f6 in f6_list:
                b2 = f6.bbox
                v2 = f6.normed_embedding
                # Compute IoU
                xA, yA = max(b1[0], b2[0]), max(b1[1], b2[1])
                xB, yB = min(b1[2], b2[2]), min(b1[3], b2[3])
                inter = max(0, xB - xA) * max(0, yB - yA)
                a1 = (b1[2] - b1[0]) * (b1[3] - b1[1])
                a2 = (b2[2] - b2[0]) * (b2[3] - b2[1])
                union = a1 + a2 - inter
                iou = inter / union if union > 0 else 0
                if iou > best_iou:
                    best_iou = iou
                    if v1 is not None and v2 is not None:
                        best_sim = float(np.dot(v1, v2))
            if best_iou > 0.5:
                ious.append(best_iou)
                if best_sim > 0:
                    cosine_similarities.append(best_sim)

    avg_cos = np.mean(cosine_similarities) if cosine_similarities else 0.0
    min_cos = np.min(cosine_similarities) if cosine_similarities else 0.0
    avg_iou = np.mean(ious) if ious else 0.0

    print(f"\n========================================================================")
    print(f"EMPIRICAL RESULTS ON ACTUAL CCTV FOOTAGE")
    print(f"========================================================================")
    print(f"Native (1280x800) Total Faces Detected : {total_faces_native}")
    print(f"Calibrated (640x640) Faces Detected    : {total_faces_640}")
    print(f"Detection Match Rate                   : {len(ious)} / {total_faces_native} ({(len(ious)/max(1, total_faces_native))*100:.1f}%)")
    print(f"Average Bounding Box IoU Overlap       : {avg_iou*100:.2f}%")
    print(f"Average ArcFace Vector Cosine Match    : {avg_cos:.4f} (1.0000 = Identical)")
    print(f"Minimum ArcFace Vector Cosine Match    : {min_cos:.4f}")
    print(f"------------------------------------------------------------------------")
    print(f"Native 1280x800 Processing Time (1 core): {t_native:.2f}s ({fps_native:.2f} FPS)")
    print(f"Calibrated 640  Processing Time (1 core): {t_640:.2f}s ({fps_640:.2f} FPS)")
    print(f"Direct Speedup Factor                  : {t_native / t_640:.2f}x FASTER")
    print(f"========================================================================\n")

if __name__ == "__main__":
    run_comparison()

