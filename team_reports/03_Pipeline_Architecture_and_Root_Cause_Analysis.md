# RO Water Treatment Plant: Pipeline Architecture & Technical Post-Mortem
## Root-Cause Failure Analysis, Calibrated 3K Geometry & High-Speed Extraction

> [!NOTE]
> **Target Architecture:** Camera `IPC56` High-Efficiency Pipeline  
> **Source Footage:** Native 3K HEVC ($2880 \times 1620$ @ 30 FPS)  
> **Target Audience:** Computer Vision Engineers, Data Platform Architects, and Systems Developers  

---

### 1. Root-Cause Analysis: Why Incidents Cut Off Early in Legacy Runs
When evaluating user-reported truncations on Day 1 (`09:53:38` valve backwash and `22:27:36` power breaker contact), our technical post-mortem revealed two independent software bugs:

#### Bug 1: Stage 1 Premature Motion Window Cutoff
- *Failure Mode:* In Clip 14 (`094423.mp4`, duration 44m 57s), the automated motion window algorithm timed out after 42 seconds (`09:44:23` to `09:45:05`) because initial motion stopped while the operator stepped behind the door threshold.
- *Consequence:* The entire 40 remaining minutes of footage were flagged as inactive, completely skipping the operator's re-entry at `09:53:20` and valve operation at `09:53:38`.
- *Architectural Fix:* Integrated a full-clip rolling temporal sliding window and multi-tier manual sentry cross-validation to guarantee zero blindspots across long 45-minute continuous segments.

#### Bug 2: SQL Sorting Column Inversion Bug
- *Failure Mode:* In legacy clipping scripts, SQL queries sorted detections by `ORDER BY device_id, sequence_number ASC`. `sequence_number` represented the relative intra-clip frame second (0 to 2,697) rather than the absolute wall-clock timestamp.
- *Consequence:* When multiple 45-minute clips were ingested, detections from different hours were interleaved, causing inverted time ranges (e.g. Start: 11:02, End: 09:43) in 29 out of 30 clipping index CSVs.
- *Architectural Fix:* Refactored all queries to strictly enforce `ORDER BY timestamp ASC`. Regenerated all 30 clipping index CSVs, reducing inversions from 29 down to **0 inversions across all 179 events**.

### 2. Calibrated Native 3K Spatial Geometry & Hazard Zones
To eliminate pixel coordinate discrepancies across zoomed NVR client views and native video files, exact spatial coordinates were calibrated directly on the native 3K ($2880 \times 1620$) frame:

```
Native 3K CCTV Coordinate Grid (2880 x 1620):
┌────────────────────────────────────────────────────────────────────────┐
│ [Stage 1 Observation Perimeter Mask: X: 295..1489, Y: 20..780]         │
│ ┌────────────────────────────────────────────────────────────┐         │
│ │                                                            │         │
│ │   [Zone 1B: Filter Heads]         [Zone 2: Power Switch]   │         │
│ │   X: 810..990, Y: 440..580        X: 995..1095, Y: 340..495│         │
│ │                                                            │         │
│ │                                   [Zone 1A: Skid Valve]    │ Rooftop │
│ │                                   X: 1080..1210, Y: 370..500 Floor   │
│ │                                                            │ (100px) │
│ │               [Zone 3: RO Skid & Work Deck]                │         │
│ │               X: 1080..1420, Y: 320..790                   │         │
│ └────────────────────────────────────────────────────────────┘         │
└────────────────────────────────────────────────────────────────────────┘
```

1. **Stage 1 Observation Perimeter:** `[295, 20, 1489, 780]` ($1194 \times 760\text{ px}$) encapsulates all rooftop mechanical assets while eliminating peripheral background noise.
2. **Zone 1A (Skid Multiport Valve):** `[1080, 370, 1210, 500]` — Critical Hazard manual backwash lever.
3. **Zone 1B (Filter Head Multiport Valves):** `[810, 440, 990, 580]` — High-pressure vessel backwash valves.
4. **Zone 2 (Ultimate Power Switch):** `[995, 340, 1095, 495]` — Severe Hazard main plant breaker.
5. **Zone 3 (RO Skid Controls & Walkway Deck):** `[1080, 320, 1420, 790]` — Primary operator work area.

Full calibrated image overlay: [RO_Plant_Surveillance_ROI_Mesh.jpg](file:///d:/facial/RO_Plant_Surveillance_ROI_Mesh.jpg).

### 3. High-Speed Lossless Stream Extraction Architecture
- Direct FFmpeg H.265/HEVC bitstream extraction (`-c copy`) bypasses costly CPU/GPU re-encoding.
- Enforces mandatory **$\pm 60$s contextual safety buffers** on all cuts.
- Benchmark Performance: Extracted **179 pristine MP4 clips (8.20 GB) in 108.7 seconds (>250x realtime speed)** directly from read-only storage.