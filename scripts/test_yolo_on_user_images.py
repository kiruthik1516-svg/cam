import cv2
import numpy as np
from ultralytics import YOLO

model = YOLO(r"d:\facial\yolov8n-pose.pt")

images = [
    ("Day 5 - 07:49:29", r"C:\Users\mkiru\.gemini\antigravity\brain\dfddef8a-f7b0-40de-8369-234a8d44ad7a\.user_uploaded\media_1793691472927_031db4d3.jpg"),
    ("Day 25 - 07:30:18", r"C:\Users\mkiru\.gemini\antigravity\brain\dfddef8a-f7b0-40de-8369-234a8d44ad7a\.user_uploaded\media_1793691515766_abd9f4c3.jpg"),
    ("Day 25 - 08:25:31", r"C:\Users\mkiru\.gemini\antigravity\brain\dfddef8a-f7b0-40de-8369-234a8d44ad7a\.user_uploaded\media_1793691507380_0ab78b78.jpg"),
    ("Day 25 - 11:17:10", r"C:\Users\mkiru\.gemini\antigravity\brain\dfddef8a-f7b0-40de-8369-234a8d44ad7a\.user_uploaded\media_1793691498529_11ea154d.jpg"),
]

for label, path in images:
    img = cv2.imread(path)
    h, w = img.shape[:2]
    res = model(img, conf=0.25, verbose=False)[0]
    print(f"\n==========================================")
    print(f"{label} (Image size: {w}x{h})")
    print(f"Detected {len(res.boxes)} persons:")
    for idx, (b, k) in enumerate(zip(res.boxes, res.keypoints)):
        box = b.xyxy[0].cpu().numpy()
        conf = float(b.conf[0])
        kpts = k.data[0].cpu().numpy()
        # KPT indices: 9 = left wrist, 10 = right wrist, 5 = left shoulder, 6 = right shoulder
        lw = kpts[9]
        rw = kpts[10]
        print(f"  Person #{idx+1}: Box=[{box[0]:.1f}, {box[1]:.1f}, {box[2]:.1f}, {box[3]:.1f}], Conf={conf:.2f}")
        print(f"    Left Wrist:  x={lw[0]:.1f}, y={lw[1]:.1f}, conf={lw[2]:.2f}")
        print(f"    Right Wrist: x={rw[0]:.1f}, y={rw[1]:.1f}, conf={rw[2]:.2f}")

