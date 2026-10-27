#!/usr/bin/env python3
"""
generate_zoomed_roi_mesh.py
Generates the Zoomed High-Definition ROI Mesh Map directly focused on the
RO Plant mechanical wing (Region of Interest: [295, 20, 1490, 780]).
"""

import cv2
import numpy as np
from pathlib import Path
import shutil

def draw_dashed_rect(img, pt1, pt2, color, thickness=1, dash_len=8):
    x1, y1 = pt1
    x2, y2 = pt2
    for x in range(x1, x2, dash_len * 2):
        cv2.line(img, (x, y1), (min(x + dash_len, x2), y1), color, thickness)
        cv2.line(img, (x, y2), (min(x + dash_len, x2), y2), color, thickness)
    for y in range(y1, y2, dash_len * 2):
        cv2.line(img, (x1, y), (x1, min(y + dash_len, y2)), color, thickness)
        cv2.line(img, (x2, y), (x2, min(y + dash_len, y2)), color, thickness)

def generate_zoomed_roi():
    base_img_path = Path("D:/facial/incident_evidence/day_01/verify_095338_extracted.jpg")
    img_full = cv2.imread(str(base_img_path))
    if img_full is None:
        print("[ERROR] Base frame not found.")
        return

    # Crop with 50px context margin around ROI [295, 20, 1490, 780]
    crop_x1, crop_y1 = 250, 0
    crop_x2, crop_y2 = 1530, 830
    roi_crop = img_full[crop_y1:crop_y2, crop_x1:crop_x2].copy()
    
    H, W = roi_crop.shape[:2]  # ~830 x 1280
    overlay = roi_crop.copy()

    # 1. Subtle 50px spatial coordinate grid
    for x in range(0, W, 50):
        alpha = 0.12 if x % 200 != 0 else 0.25
        cv2.line(overlay, (x, 0), (x, H), (140, 175, 195), 1)
        if x % 100 == 0 and x > 0:
            native_x = crop_x1 + x
            cv2.putText(roi_crop, f"X:{native_x}", (x + 4, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (180, 215, 235), 1, cv2.LINE_AA)

    for y in range(0, H, 50):
        cv2.line(overlay, (0, y), (W, y), (140, 175, 195), 1)
        if y % 100 == 0 and y > 60:
            native_y = crop_y1 + y
            cv2.putText(roi_crop, f"Y:{native_y}", (10, y - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (180, 215, 235), 1, cv2.LINE_AA)

    cv2.addWeighted(overlay, 0.22, roi_crop, 0.78, 0, roi_crop)

    # 2. Outer Access Perimeter [295, 20, 1490, 780] mapped into crop
    p_x1 = 295 - crop_x1
    p_y1 = 20 - crop_y1
    p_x2 = 1490 - crop_x1
    p_y2 = 780 - crop_y1
    cv2.rectangle(roi_crop, (p_x1, p_y1), (p_x2, p_y2), (255, 215, 0), 2, cv2.LINE_AA)
    cv2.putText(roi_crop, "STAGE 1 CORE GATING ROI [295, 20, 1490, 780]", (p_x1 + 10, p_y1 + 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 235, 80), 2, cv2.LINE_AA)

    # 3. Equipment Zones (mapped to crop)
    zones = [
        {
            "id": "ZONE 1A",
            "name": "Skid Backwash Valve (Manual Incident 09:53:38)",
            "hazard": "CRITICAL",
            "bbox_native": [1080, 370, 1210, 500],
            "color": (0, 30, 235),
            "bg_badge": (0, 15, 160),
            "badge_pos": (p_x1 + 680, p_y1 + 510),
            "badge_size": (350, 48)
        },
        {
            "id": "ZONE 1B",
            "name": "Dual Media Filter Multiport Heads",
            "hazard": "CRITICAL",
            "bbox_native": [810, 440, 990, 580],
            "color": (0, 140, 255),
            "bg_badge": (0, 90, 180),
            "badge_pos": (p_x1 + 280, p_y1 + 590),
            "badge_size": (340, 48)
        },
        {
            "id": "ZONE 2",
            "name": "Ultimate Power Switch (Manual Incident 22:27:36)",
            "hazard": "SEVERE",
            "bbox_native": [995, 340, 1095, 495],
            "color": (210, 0, 220),
            "bg_badge": (140, 0, 150),
            "badge_pos": (p_x1 + 480, p_y1 + 260),
            "badge_size": (360, 48)
        },
        {
            "id": "ZONE 3",
            "name": "RO Skid & Operator Deck (corridor threshold)",
            "hazard": "ELEVATED",
            "bbox_native": [1080, 320, 1420, 790],
            "color": (220, 190, 0),
            "bg_badge": (130, 110, 0),
            "badge_pos": (p_x1 + 840, p_y1 + 750),
            "badge_size": (340, 48)
        }
    ]

    for z in zones:
        nx1, ny1, nx2, ny2 = z["bbox_native"]
        zx1, zy1 = nx1 - crop_x1, ny1 - crop_y1
        zx2, zy2 = nx2 - crop_x1, ny2 - crop_y1
        col = z["color"]

        # Proximity buffer (40px)
        draw_dashed_rect(roi_crop, (max(0, zx1 - 40), max(0, zy1 - 40)), 
                         (min(W, zx2 + 40), min(H, zy2 + 40)), (0, 255, 255), thickness=1, dash_len=6)

        # Translucent fill
        overlay = roi_crop.copy()
        cv2.rectangle(overlay, (zx1, zy1), (zx2, zy2), col, -1)
        cv2.addWeighted(overlay, 0.25, roi_crop, 0.75, 0, roi_crop)

        # Crisp solid box
        cv2.rectangle(roi_crop, (zx1, zy1), (zx2, zy2), col, 2, cv2.LINE_AA)

        # Crosshair
        cx, cy = (zx1 + zx2) // 2, (zy1 + zy2) // 2
        cv2.line(roi_crop, (cx - 8, cy), (cx + 8, cy), (255, 255, 255), 1)
        cv2.line(roi_crop, (cx, cy - 8), (cx, cy + 8), (255, 255, 255), 1)

        # Callout badge
        bx1, by1 = z["badge_pos"]
        bw, bh = z["badge_size"]
        bx1 = max(10, min(W - bw - 10, bx1))
        by1 = max(70, min(H - bh - 10, by1))
        bx2, by2 = bx1 + bw, by1 + bh

        cv2.rectangle(roi_crop, (bx1 + 2, by1 + 2), (bx2 + 2, by2 + 2), (15, 15, 15), -1)
        cv2.rectangle(roi_crop, (bx1, by1), (bx2, by2), z["bg_badge"], -1)
        cv2.rectangle(roi_crop, (bx1, by1), (bx2, by2), col, 1, cv2.LINE_AA)

        cv2.putText(roi_crop, f"[{z['id']}] {z['hazard']} HAZARD", (bx1 + 8, by1 + 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(roi_crop, z["name"], (bx1 + 8, by1 + 38),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, (225, 240, 255), 1, cv2.LINE_AA)

        # Connecting line
        badge_anchor = (bx1 + 15, by1 if by1 > cy else by2)
        cv2.line(roi_crop, badge_anchor, (cx, cy), col, 1, cv2.LINE_AA)
        cv2.circle(roi_crop, (cx, cy), 3, (255, 255, 255), -1)

    # 4. Top Telemetry Header
    hud_h = 65
    overlay = roi_crop.copy()
    cv2.rectangle(overlay, (0, 0), (W, hud_h), (12, 16, 22), -1)
    cv2.addWeighted(overlay, 0.88, roi_crop, 0.12, 0, roi_crop)
    cv2.line(roi_crop, (0, hud_h), (W, hud_h), (0, 215, 255), 2)

    cv2.putText(roi_crop, "RO WATER TREATMENT PLANT - HIGH-DEFINITION REGION OF INTEREST (ROI) MAP", (20, 26),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(roi_crop, "CAMERA: IPC56 | ZOOMED PRIMARY GATING PERIMETER [295, 20, 1490, 780] | 50px CARTESIAN MESH",
                (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (0, 215, 255), 1, cv2.LINE_AA)

    out_jpg = Path("D:/facial/RO_Plant_Zoomed_ROI_Mesh.jpg")
    cv2.imwrite(str(out_jpg), roi_crop, [cv2.IMWRITE_JPEG_QUALITY, 96])
    print(f"[OK] Saved Zoomed ROI Mesh: {out_jpg} ({out_jpg.stat().st_size / (1024*1024):.2f} MB)")

    # Copy to brain artifact directory
    artifact_dir = Path("C:/Users/mkiru/.gemini/antigravity/brain/8c6e85a2-8ea1-4c6c-bb23-a9aed5b45fc6")
    if artifact_dir.exists():
        shutil.copy2(str(out_jpg), str(artifact_dir / "RO_Plant_Zoomed_ROI_Mesh.jpg"))
        print(f"[OK] Copied to artifact directory: {artifact_dir / 'RO_Plant_Zoomed_ROI_Mesh.jpg'}")

if __name__ == "__main__":
    generate_zoomed_roi()
