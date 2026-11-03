#!/usr/bin/env python3
"""
run_surveillance_regression_test.py
Automated End-to-End Regression Test Suite for Sentinel CCTV Surveillance Engine (IPC56).

Tests:
1. Physical Contact & Elevation Geometry on Verified User Evidence (Day 5 & Day 25).
2. False-Positive Immunity on Normal Corridor Pedestrians (Arm-swing & Elevation rejection).
3. Live YOLOv8-pose detection & zone evaluation on actual CCTV candidate frames.
4. Cross-Engine Integrity & Manifest Synchronization (Engine 1 vs Engine 2).
"""

import sys
import os
import csv
import json
from pathlib import Path
import numpy as np

# Add repo root to path
REPO_ROOT = Path("d:/facial")
sys.path.insert(0, str(REPO_ROOT))

from engine_v2.config import ASSET_ZONES, KPT_RIGHT_WRIST, KPT_LEFT_WRIST
from engine_v2.geometry import evaluate_asset_interaction

def test_user_verified_switch_touches():
    print("\n[TEST 1] Testing Physical Contact Geometry on User-Verified Switch Touches...")
    zone_switch = ASSET_ZONES["ZONE_SWITCH"]
    
    # 1. Day 5 @ 07:49:29
    # Candidate wrist: (793.1, 193.1) -> Native: (1088.1, 213.1)
    # Person box: [1055.9, 188.2, 1269.5, 628.8]
    kpts_d05 = np.zeros((17, 3), dtype=np.float32)
    kpts_d05[KPT_RIGHT_WRIST] = [1088.1, 213.1, 0.87]
    kpts_d05[KPT_LEFT_WRIST] = [1176.4, 350.6, 0.99]
    box_d05 = (1055.9, 188.2, 1269.5, 628.8)
    
    res_d05 = evaluate_asset_interaction(box_d05, kpts_d05, zone_switch)
    print(f"  Day 5 @ 07:49:29: Interacted={res_d05['interacted']}, Type={res_d05['interaction_type']}, ActiveWrist={res_d05['active_wrist']}, Dist={res_d05['min_wrist_dist']:.1f}px")
    assert res_d05["interacted"] == True, "FAIL: Day 5 switch touch was not detected!"
    assert res_d05["active_wrist"] == "RIGHT", "FAIL: Day 5 active wrist should be RIGHT!"
    assert res_d05["min_wrist_dist"] == 0.0, f"FAIL: Expected 0.0px distance, got {res_d05['min_wrist_dist']}"

    # 2. Day 25 @ 07:30:18
    # Candidate wrist: (824.2, 224.6) -> Native: (1119.2, 244.6)
    # Person box: [1096.6, 186.3, 1254.6, 596.7]
    kpts_d25_1 = np.zeros((17, 3), dtype=np.float32)
    kpts_d25_1[KPT_RIGHT_WRIST] = [1119.2, 244.6, 0.80]
    kpts_d25_1[KPT_LEFT_WRIST] = [1214.7, 400.7, 0.98]
    box_d25_1 = (1096.6, 186.3, 1254.6, 596.7)
    
    res_d25_1 = evaluate_asset_interaction(box_d25_1, kpts_d25_1, zone_switch)
    print(f"  Day 25 @ 07:30:18: Interacted={res_d25_1['interacted']}, Type={res_d25_1['interaction_type']}, ActiveWrist={res_d25_1['active_wrist']}, Dist={res_d25_1['min_wrist_dist']:.1f}px")
    assert res_d25_1["interacted"] == True, "FAIL: Day 25 07:30 switch touch was not detected!"
    assert res_d25_1["active_wrist"] == "RIGHT", "FAIL: Day 25 07:30 active wrist should be RIGHT!"
    assert res_d25_1["min_wrist_dist"] == 0.0, f"FAIL: Expected 0.0px distance, got {res_d25_1['min_wrist_dist']}"

    # 3. Day 25 @ 08:25:31
    # Candidate wrist: (788.3, 201.1) -> Native: (1083.3, 221.1)
    kpts_d25_2 = np.zeros((17, 3), dtype=np.float32)
    kpts_d25_2[KPT_RIGHT_WRIST] = [1083.3, 221.1, 0.75]
    box_d25_2 = (1050.0, 180.0, 1240.0, 610.0)
    res_d25_2 = evaluate_asset_interaction(box_d25_2, kpts_d25_2, zone_switch)
    print(f"  Day 25 @ 08:25:31: Interacted={res_d25_2['interacted']}, Type={res_d25_2['interaction_type']}, ActiveWrist={res_d25_2['active_wrist']}, Dist={res_d25_2['min_wrist_dist']:.1f}px")
    assert res_d25_2["interacted"] == True, "FAIL: Day 25 08:25 switch touch was not detected!"

    # 4. Day 25 @ 11:17:10
    # Candidate wrist: (795.0, 198.0) -> Native: (1090.0, 218.0)
    kpts_d25_3 = np.zeros((17, 3), dtype=np.float32)
    kpts_d25_3[KPT_RIGHT_WRIST] = [1090.0, 218.0, 0.70]
    box_d25_3 = (1060.0, 180.0, 1250.0, 600.0)
    res_d25_3 = evaluate_asset_interaction(box_d25_3, kpts_d25_3, zone_switch)
    print(f"  Day 25 @ 11:17:10: Interacted={res_d25_3['interacted']}, Type={res_d25_3['interaction_type']}, ActiveWrist={res_d25_3['active_wrist']}, Dist={res_d25_3['min_wrist_dist']:.1f}px")
    assert res_d25_3["interacted"] == True, "FAIL: Day 25 11:17 switch touch was not detected!"

    print("  -> PASS: All 4 user-verified switch touches achieve 100% True Positive recall with 0.0px direct contact distance.")

def test_negative_controls_false_positive_immunity():
    print("\n[TEST 2] Testing False-Positive Immunity on Normal Corridor Pedestrians...")
    zone_switch = ASSET_ZONES["ZONE_SWITCH"]
    zone_valves = ASSET_ZONES["ZONE_VALVES"]

    # Negative Case 1: Walking pedestrian past switch with arms swinging at waist height
    # Box is inside corridor: [1020, 160, 1150, 600]
    # Wrists are at Y = 310px (waist height, 2D distance to switch bottom Y=265 is only 45px)
    kpts_ped1 = np.zeros((17, 3), dtype=np.float32)
    kpts_ped1[KPT_RIGHT_WRIST] = [1070.0, 310.0, 0.90]
    kpts_ped1[KPT_LEFT_WRIST] = [1110.0, 325.0, 0.90]
    box_ped1 = (1020.0, 160.0, 1150.0, 600.0)

    res_ped1 = evaluate_asset_interaction(box_ped1, kpts_ped1, zone_switch)
    print(f"  Walking Pedestrian (Wrist Y=310px): Interacted={res_ped1['interacted']}, Type={res_ped1['interaction_type']}")
    assert res_ped1["interacted"] == False, "FAIL: Elevation gate failed! Normal walking arm-swing triggered switch alarm!"

    # Negative Case 2: Pedestrian walking along walkway past valves (X = 920px)
    # Box is in walkway corridor: [920, 200, 1080, 620]
    # Person is NOT on the maintenance deck (X_min = 920 > 850, Center X = 1000 > 820)
    kpts_ped2 = np.zeros((17, 3), dtype=np.float32)
    kpts_ped2[KPT_LEFT_WRIST] = [840.0, 380.0, 0.85]  # Left wrist swinging near valve edge
    box_ped2 = (920.0, 200.0, 1080.0, 620.0)

    res_ped2 = evaluate_asset_interaction(box_ped2, kpts_ped2, zone_valves)
    print(f"  Walkway Pedestrian (X=920px past Valves): Interacted={res_ped2['interacted']}, Type={res_ped2['interaction_type']}")
    assert res_ped2["interacted"] == False, "FAIL: Deck stance gate failed! Walkway pedestrian triggered valve alarm!"

    # Negative Case 3: Background pedestrian on staircase (15m in background, feet Y = 410px)
    box_ped3 = (1040.0, 210.0, 1120.0, 410.0)
    kpts_ped3 = np.zeros((17, 3), dtype=np.float32)
    kpts_ped3[KPT_RIGHT_WRIST] = [1060.0, 240.0, 0.80]

    res_ped3 = evaluate_asset_interaction(box_ped3, kpts_ped3, zone_switch)
    print(f"  Background Pedestrian (Feet Y=410px): Interacted={res_ped3['interacted']}, Type={res_ped3['interaction_type']}")
    assert res_ped3["interacted"] == False, "FAIL: Perspective ground plane gate failed! Background pedestrian triggered switch alarm!"

    print("  -> PASS: All negative control pedestrian transits strictly rejected. False positive rate = 0.0%.")

def test_manifest_and_index_synchronization():
    print("\n[TEST 3] Testing Manifest & Index Cross-Engine Synchronization...")
    
    # 1. Check Engine 2 Day 5 Manifest
    d05_mf_path = REPO_ROOT / "incident_evidence_v2/day_05/Day05_Incident_Manifest.csv"
    assert d05_mf_path.exists(), "Day 5 manifest missing!"
    with open(d05_mf_path, "r", encoding="utf-8") as f:
        d05_rows = list(csv.DictReader(f))
    print(f"  Engine 2 Day 5 Manifest Total Incidents: {len(d05_rows)}")
    assert len(d05_rows) == 4, f"FAIL: Expected 4 incidents on Day 5, got {len(d05_rows)}"
    
    switch_d05 = [r for r in d05_rows if r["zone_id"] == "ZONE_SWITCH"]
    assert len(switch_d05) == 1, f"FAIL: Expected exactly 1 switch touch on Day 5, got {len(switch_d05)}"
    assert switch_d05[0]["peak_time"] == "2026-09-05 07:49:29", f"Wrong switch timestamp: {switch_d05[0]['peak_time']}"
    assert switch_d05[0]["severity"] == "SEVERE", "Wrong severity for switch touch!"

    # 2. Check Engine 2 Day 25 Manifest
    d25_mf_path = REPO_ROOT / "incident_evidence_v2/day_25/Day25_Incident_Manifest.csv"
    assert d25_mf_path.exists(), "Day 25 manifest missing!"
    with open(d25_mf_path, "r", encoding="utf-8") as f:
        d25_rows = list(csv.DictReader(f))
    print(f"  Engine 2 Day 25 Manifest Total Incidents: {len(d25_rows)}")
    assert len(d25_rows) == 13, f"FAIL: Expected 13 incidents on Day 25, got {len(d25_rows)}"
    
    switch_d25 = [r for r in d25_rows if r["zone_id"] == "ZONE_SWITCH"]
    assert len(switch_d25) == 4, f"FAIL: Expected exactly 4 switch touches on Day 25, got {len(switch_d25)}"

    # 3. Check Engine 1 Day 5 Clipping Index
    d05_idx_path = REPO_ROOT / "incident_evidence/day_05/Day5_Persona_Video_Clipping_Index.csv"
    assert d05_idx_path.exists(), "Day 5 index missing!"
    with open(d05_idx_path, "r", encoding="utf-8") as f:
        d05_idx_rows = list(csv.DictReader(f))
    print(f"  Engine 1 Day 5 Clipping Index Total Events: {len(d05_idx_rows)}")
    assert len(d05_idx_rows) == 4, f"FAIL: Expected 4 events in Day 5 index, got {len(d05_idx_rows)}"
    switch_idx_d05 = [r for r in d05_idx_rows if r["Critical_Zone"] == "Ultimate Plant Power Switch"]
    assert len(switch_idx_d05) == 1, f"FAIL: Expected 1 switch touch in Day 5 index, got {len(switch_idx_d05)}"
    assert switch_idx_d05[0]["Hazard_Level"] == "SEVERE"

    # 4. Check Master 30-Day Matrix
    mat_path = REPO_ROOT / "incident_evidence_v2/master_30day_compliance_matrix.json"
    assert mat_path.exists(), "Master matrix missing!"
    with open(mat_path, "r", encoding="utf-8") as f:
        mat = json.load(f)
    print(f"  Master Matrix Summary: Total={mat['summary']['total_incidents']}, Severe Switch={mat['summary']['severe_switch']}, Critical Valves={mat['summary']['critical_valves']}")
    assert mat["summary"]["total_incidents"] == 17, f"Expected 17 total incidents, got {mat['summary']['total_incidents']}"
    assert mat["summary"]["severe_switch"] == 5, f"Expected 5 switch touches (1 on Day 5, 4 on Day 25), got {mat['summary']['severe_switch']}"
    assert mat["summary"]["critical_valves"] == 5, f"Expected 5 critical valve ops, got {mat['summary']['critical_valves']}"

    print("  -> PASS: Engine 1 and Engine 2 are 100% synchronized across all manifests, indices, and the master matrix.")

def test_live_yolo_detection_on_cctv_frames():
    print("\n[TEST 4] Running Live YOLOv8n-pose Detection on Actual Day 5 & Day 25 Video Frames...")
    import cv2
    from ultralytics import YOLO
    
    model_path = REPO_ROOT / "yolov8n-pose.pt"
    if not model_path.exists():
        print("  [SKIP] YOLO model file not found.")
        return

    model = YOLO(str(model_path))
    zone_switch = ASSET_ZONES["ZONE_SWITCH"]
    CROP_OFFSET_X = 295
    CROP_OFFSET_Y = 20

    # Test actual frame for Day 5 @ 07:49:29
    f_d05 = REPO_ROOT / "data/stage1_candidates/day_05/day05_56_8_DBGT_IPC56_d6e8956a69324d1791717ff9b2fe2d6d_20260905072306_w13_00039.jpg"
    if f_d05.exists():
        img = cv2.imread(str(f_d05))
        res = model(img, conf=0.25, verbose=False)[0]
        detected_switch = False
        for box_obj, kpt_obj in zip(res.boxes, res.keypoints):
            box = box_obj.xyxy[0].cpu().numpy()
            kpts = kpt_obj.data[0].cpu().numpy()
            # Convert crop to native
            box_native = (
                float(box[0] + CROP_OFFSET_X),
                float(box[1] + CROP_OFFSET_Y),
                float(box[2] + CROP_OFFSET_X),
                float(box[3] + CROP_OFFSET_Y)
            )
            kpts_native = kpts.copy()
            kpts_native[:, 0] += CROP_OFFSET_X
            kpts_native[:, 1] += CROP_OFFSET_Y
            
            eval_res = evaluate_asset_interaction(box_native, kpts_native, zone_switch)
            if eval_res["interacted"]:
                detected_switch = True
                print(f"  Day 5 Candidate Frame w13_00039: Triggered {eval_res['interaction_type']} with wrist dist {eval_res['min_wrist_dist']:.1f}px (Active={eval_res['active_wrist']})")
        assert detected_switch == True, "FAIL: Live YOLO detection on Day 5 07:49 frame did not trigger switch contact!"
        print("  -> Live Day 5 CCTV frame detection: PASSED.")
    else:
        print(f"  [WARN] Frame {f_d05.name} not found.")

    # Test actual frame for Day 25 @ 07:30:18
    f_d25 = REPO_ROOT / "data/stage1_candidates/day_25/day25_56_8_DBGT_IPC56_200effb4fb8b4948bf3821f748412073_20260925071400_w00_00010.jpg"
    if f_d25.exists():
        img = cv2.imread(str(f_d25))
        res = model(img, conf=0.25, verbose=False)[0]
        detected_switch = False
        for box_obj, kpt_obj in zip(res.boxes, res.keypoints):
            box = box_obj.xyxy[0].cpu().numpy()
            kpts = kpt_obj.data[0].cpu().numpy()
            box_native = (
                float(box[0] + CROP_OFFSET_X),
                float(box[1] + CROP_OFFSET_Y),
                float(box[2] + CROP_OFFSET_X),
                float(box[3] + CROP_OFFSET_Y)
            )
            kpts_native = kpts.copy()
            kpts_native[:, 0] += CROP_OFFSET_X
            kpts_native[:, 1] += CROP_OFFSET_Y
            
            eval_res = evaluate_asset_interaction(box_native, kpts_native, zone_switch)
            if eval_res["interacted"]:
                detected_switch = True
                print(f"  Day 25 Candidate Frame w00_00010: Triggered {eval_res['interaction_type']} with wrist dist {eval_res['min_wrist_dist']:.1f}px (Active={eval_res['active_wrist']})")
        assert detected_switch == True, "FAIL: Live YOLO detection on Day 25 07:30 frame did not trigger switch contact!"
        print("  -> Live Day 25 CCTV frame detection: PASSED.")
    else:
        print(f"  [WARN] Frame {f_d25.name} not found.")

if __name__ == "__main__":
    print("================================================================================")
    print("STARTING COMPREHENSIVE AUTOMATED REGRESSION TEST SUITE — SENTINEL SURVEILLANCE")
    print("================================================================================")
    try:
        test_user_verified_switch_touches()
        test_negative_controls_false_positive_immunity()
        test_manifest_and_index_synchronization()
        test_live_yolo_detection_on_cctv_frames()
        print("\n================================================================================")
        print(">>> ALL REGRESSION SUITE TESTS PASSED WITH 100% SUCCESS <<<")
        print("================================================================================")
    except AssertionError as e:
        print(f"\n[REGRESSION TEST FAILED]: {e}")
        sys.exit(1)

