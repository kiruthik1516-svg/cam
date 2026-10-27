#!/usr/bin/env python3
"""
generate_roi_mesh_image.py
Generates the calibrated Spatial ROI Mesh & Equipment Protection Zone Map
overlaid on the native 3K CCTV frame for Camera IPC56 (RO Water Treatment Plant Rooftop).
"""

import cv2
import numpy as np
from pathlib import Path
import shutil

def draw_dashed_rect(img, pt1, pt2, color, thickness=1, dash_len=12):
    x1, y1 = pt1
    x2, y2 = pt2
    # Top and bottom
    for x in range(x1, x2, dash_len * 2):
        cv2.line(img, (x, y1), (min(x + dash_len, x2), y1), color, thickness)
        cv2.line(img, (x, y2), (min(x + dash_len, x2), y2), color, thickness)
    # Left and right
    for y in range(y1, y2, dash_len * 2):
        cv2.line(img, (x1, y), (x1, min(y + dash_len, y2)), color, thickness)
        cv2.line(img, (x2, y), (x2, min(y + dash_len, y2)), color, thickness)

def generate_roi_mesh():
    base_img_path = Path("D:/facial/incident_evidence/day_01/verify_095338_extracted.jpg")
    if not base_img_path.exists():
        base_img_path = Path("D:/facial/incident_evidence/verify_095338_extracted.jpg")

    img = cv2.imread(str(base_img_path))
    if img is None:
        print("[ERROR] Base frame not found.")
        return

    H, W = img.shape[:2]  # 1620, 2880
    overlay = img.copy()

    # 1. Subtle Spatial Grid Mesh (100px intervals)
    grid_spacing = 100
    for x in range(0, W, grid_spacing):
        alpha_val = 0.12 if x % 500 != 0 else 0.28
        cv2.line(overlay, (x, 0), (x, H), (120, 160, 185), 1)
        if x % 200 == 0 and x > 0:
            cv2.putText(img, f"X:{x}", (x + 6, 125), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (170, 205, 225), 1, cv2.LINE_AA)

    for y in range(0, H, grid_spacing):
        cv2.line(overlay, (0, y), (W, y), (120, 160, 185), 1)
        if y % 200 == 0 and y > 100:
            cv2.putText(img, f"Y:{y}", (12, y - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (170, 205, 225), 1, cv2.LINE_AA)

    # Blend grid
    cv2.addWeighted(overlay, 0.18, img, 0.82, 0, img)
    overlay = img.copy()

    # 2. Stage 1 Calibrated Core Observation Perimeter [295, 20, 1489, 780]
    p_x1, p_y1, p_x2, p_y2 = 295, 20, 1489, 780
    cv2.rectangle(overlay, (p_x1, p_y1), (p_x2, p_y2), (255, 215, 0), -1)
    cv2.addWeighted(overlay, 0.08, img, 0.92, 0, img)
    cv2.rectangle(img, (p_x1, p_y1), (p_x2, p_y2), (255, 215, 0), 2, cv2.LINE_AA)
    cv2.putText(img, "STAGE 1 CORE OBSERVATION PERIMETER [295, 20, 1489, 780] (1194x760)", 
                (p_x1 + 15, p_y1 + 125), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 235, 80), 2, cv2.LINE_AA)

    # 3. Critical Equipment Protection Zones (Calibrated Native 3K Coordinates)
    zones = [
        {
            "id": "ZONE 1A",
            "name": "Skid Multiport Backwash Valve",
            "hazard": "CRITICAL HAZARD",
            "detail": "09:53:38 Incident Point",
            "bbox": [1080, 370, 1210, 500],
            "color_bgr": (0, 30, 235),      # Crisp Red
            "bg_badge": (0, 15, 160),
            "badge_pos": (1080, 515),
            "badge_size": (370, 58)
        },
        {
            "id": "ZONE 1B",
            "name": "Filter Media Vessel Head Valves",
            "hazard": "CRITICAL HAZARD",
            "detail": "High-Pressure Hydraulic Valves",
            "bbox": [810, 440, 990, 580],
            "color_bgr": (0, 140, 255),     # Vibrant Orange
            "bg_badge": (0, 90, 180),
            "badge_pos": (620, 595),
            "badge_size": (370, 58)
        },
        {
            "id": "ZONE 2",
            "name": "Ultimate Plant Power Switch",
            "hazard": "SEVERE HAZARD",
            "detail": "22:27:36 Incident Point",
            "bbox": [995, 340, 1095, 495],
            "color_bgr": (210, 0, 220),     # Bright Magenta
            "bg_badge": (140, 0, 150),
            "badge_pos": (850, 270),
            "badge_size": (360, 58)
        },
        {
            "id": "ZONE 3",
            "name": "RO Skid & Operator Work Deck",
            "hazard": "ELEVATED MONITORING",
            "detail": "Access Corridor & Skid Deck",
            "bbox": [1080, 320, 1420, 790],
            "color_bgr": (220, 190, 0),     # Bright Cyan / Aqua
            "bg_badge": (130, 110, 0),
            "badge_pos": (1230, 805),
            "badge_size": (380, 58)
        }
    ]

    for z in zones:
        x1, y1, x2, y2 = z["bbox"]
        col = z["color_bgr"]

        # 40px Proximity buffer ring (dashed yellow)
        margin = 40
        draw_dashed_rect(img, (max(0, x1 - margin), max(0, y1 - margin)), 
                         (min(W, x2 + margin), min(H, y2 + margin)), (0, 255, 255), thickness=1, dash_len=8)

        # Translucent fill
        overlay = img.copy()
        cv2.rectangle(overlay, (x1, y1), (x2, y2), col, -1)
        cv2.addWeighted(overlay, 0.28, img, 0.72, 0, img)

        # Solid bounding box
        cv2.rectangle(img, (x1, y1), (x2, y2), col, 2, cv2.LINE_AA)

        # Center crosshair
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        ch_len = 10
        cv2.line(img, (cx - ch_len, cy), (cx + ch_len, cy), (255, 255, 255), 1)
        cv2.line(img, (cx, cy - ch_len), (cx, cy + ch_len), (255, 255, 255), 1)

        # Callout Badge Banner
        bx1, by1 = z["badge_pos"]
        bw, bh = z["badge_size"]
        bx2, by2 = bx1 + bw, by1 + bh

        # Keep badge within screen
        bx1 = max(10, min(W - bw - 10, bx1))
        by1 = max(105, min(H - bh - 10, by1))
        bx2, by2 = bx1 + bw, by1 + bh

        # Shadow & Box
        cv2.rectangle(img, (bx1 + 3, by1 + 3), (bx2 + 3, by2 + 3), (15, 15, 15), -1)
        cv2.rectangle(img, (bx1, by1), (bx2, by2), z["bg_badge"], -1)
        cv2.rectangle(img, (bx1, by1), (bx2, by2), col, 2, cv2.LINE_AA)

        # Text labels
        cv2.putText(img, f"[{z['id']}] {z['hazard']}", (bx1 + 10, by1 + 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(img, f"{z['name']} ({z['detail']})", (bx1 + 10, by1 + 45),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.44, (225, 240, 255), 1, cv2.LINE_AA)

        # Pointer line connecting badge to zone center
        target_pt = (cx, cy)
        badge_anchor = (bx1 + 20, by1 if by1 > cy else by2)
        cv2.line(img, badge_anchor, target_pt, col, 1, cv2.LINE_AA)
        cv2.circle(img, target_pt, 4, (255, 255, 255), -1)

    # 4. Top Telemetry HUD Header
    hud_h = 100
    overlay = img.copy()
    cv2.rectangle(overlay, (0, 0), (W, hud_h), (12, 16, 22), -1)
    cv2.addWeighted(overlay, 0.88, img, 0.12, 0, img)
    cv2.line(img, (0, hud_h), (W, hud_h), (0, 215, 255), 2)

    # Title & Telemetry text
    cv2.putText(img, "RO WATER TREATMENT PLANT - FACILITY SURVEILLANCE & BIOMETRIC AUDIT", (25, 38),
                cv2.FONT_HERSHEY_SIMPLEX, 0.95, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(img, "CAMERA: IPC56 (Rooftop Deck) | NATIVE 3K HEVC (2880x1620 @ 30 FPS) | CALIBRATED ROI MESH & HAZARD ZONES",
                (25, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (0, 215, 255), 1, cv2.LINE_AA)

    # Right-side HUD Legend
    leg_x = W - 820
    cv2.rectangle(img, (leg_x, 12), (W - 20, 88), (20, 25, 32), -1)
    cv2.rectangle(img, (leg_x, 12), (W - 20, 88), (65, 80, 95), 1)

    # Legend items row 1
    cv2.rectangle(img, (leg_x + 15, 25), (leg_x + 35, 41), (0, 30, 235), -1)
    cv2.putText(img, "Zone 1A/B: Valves (Critical)", (leg_x + 45, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (230, 230, 230), 1)

    cv2.rectangle(img, (leg_x + 280, 25), (leg_x + 300, 41), (210, 0, 220), -1)
    cv2.putText(img, "Zone 2: Power Switch (Severe)", (leg_x + 310, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (230, 230, 230), 1)

    cv2.rectangle(img, (leg_x + 550, 25), (leg_x + 570, 41), (220, 190, 0), -1)
    cv2.putText(img, "Zone 3: Skid Deck (Elevated)", (leg_x + 580, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (230, 230, 230), 1)

    # Legend items row 2
    draw_dashed_rect(img, (leg_x + 15, 55), (leg_x + 35, 71), (0, 255, 255), thickness=1, dash_len=4)
    cv2.putText(img, "40px Proximity Threshold", (leg_x + 45, 68), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (200, 225, 225), 1)

    cv2.putText(img, "Direct Contact: IoU > 0.08", (leg_x + 280, 68), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (200, 225, 225), 1)
    cv2.putText(img, "DBSCAN: eps=0.38 / 512-D", (leg_x + 550, 68), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (200, 225, 225), 1)

    # Save outputs
    out_jpg = Path("D:/facial/RO_Plant_Surveillance_ROI_Mesh.jpg")
    out_png = Path("D:/facial/RO_Plant_Surveillance_ROI_Mesh.png")
    cv2.imwrite(str(out_jpg), img, [cv2.IMWRITE_JPEG_QUALITY, 96])
    cv2.imwrite(str(out_png), img)
    print(f"[OK] Generated: {out_jpg} ({out_jpg.stat().st_size / (1024*1024):.2f} MB)")
    print(f"[OK] Generated: {out_png} ({out_png.stat().st_size / (1024*1024):.2f} MB)")

    # Copy to brain artifact directory
    artifact_dir = Path("C:/Users/mkiru/.gemini/antigravity/brain/8c6e85a2-8ea1-4c6c-bb23-a9aed5b45fc6")
    if artifact_dir.exists():
        shutil.copy2(str(out_jpg), str(artifact_dir / "RO_Plant_Surveillance_ROI_Mesh.jpg"))
        shutil.copy2(str(out_png), str(artifact_dir / "RO_Plant_Surveillance_ROI_Mesh.png"))
        print(f"[OK] Copied to artifact directory: {artifact_dir / 'RO_Plant_Surveillance_ROI_Mesh.jpg'}")

if __name__ == "__main__":
    generate_roi_mesh()

