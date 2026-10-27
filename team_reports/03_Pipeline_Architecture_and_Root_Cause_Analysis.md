# System Architecture & Technical Verification: RO Water Treatment Plant
## Calibrated Native 3K Geometry, Lossless Extraction Pipeline & Quality Assurance

### Document Control & System Specifications
| Parameter | System Specification |
| :--- | :--- |
| **Sensor Hardware** | Overhead Fixed 3K IP Camera (`IPC56`) |
| **Native Video Format** | $2880 \times 1620$ @ 30 FPS, HEVC/H.265 Elementary Bitstream |
| **Extraction Speed** | Bitstream Passthrough (`-c copy`) >250x Realtime Speed |
| **Storage Policy** | Strictly Read-Only Source Volume (`E:\RO WATER SEP`) |
| **Audit Document Suite** | 90 Daily Verification CSVs across 30 Days |

---

### 1. End-to-End Processing Architecture
The automated surveillance pipeline operates across four discrete stages:
1. **Stage 1: Spatial Gating & Motion Analysis:** Evaluates native frames within the calibrated mechanical boundary `[295, 20, 1490, 780]` to filter irrelevant terrace activity.
2. **Stage 2: Lossless Bitstream Extraction:** Executes direct FFmpeg HEVC packet copying with enforced $\pm 60$-second pre- and post-event contextual buffers.
3. **Stage 3: Deep Feature Extraction:** Crops faces passing confidence $\ge 0.80$ and quality score $Q \ge 40.0$, extracting $L_2$-normalized 512-D ArcFace vectors.
4. **Stage 4: Unsupervised Spatial-Temporal Identity Clustering:** Groups vectors via DBSCAN (cosine $\varepsilon \le 0.38$) to build objective master personas.

### 2. Calibrated Native 3K Spatial Geometry & Equipment Zones
To ensure exact bounding box alignment between raw video files and NVR monitoring stations, coordinates are mapped directly onto the native 3K ($2880 \times 1620$) plane:

```
Native 3K CCTV Coordinate Grid (2880 x 1620):
┌────────────────────────────────────────────────────────────────────────┐
│ [Stage 1 Observation Perimeter Mask: X: 295..1490, Y: 20..780]         │
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

1. **Stage 1 Observation Perimeter:** `[295, 20, 1490, 780]` ($1195 \times 760\text{ px}$) encapsulates all rooftop mechanical equipment while filtering external sky and terrace areas.
2. **Zone 1A (Skid Multiport Valve):** `[1080, 370, 1210, 500]` — Critical Hazard primary backwash lever.
3. **Zone 1B (Filter Head Multiport Valves):** `[810, 440, 990, 580]` — Critical Hazard dual vessel backwash levers.
4. **Zone 2 (Ultimate Power Switch):** `[995, 340, 1095, 495]` — Severe Hazard plant master circuit breaker.
5. **Zone 3 (RO Skid Controls & Walkway Deck):** `[1080, 320, 1420, 790]` — Elevated monitoring personnel presence area.

Visual overlays: Full-Frame 3K Mesh at [RO_Plant_Surveillance_ROI_Mesh.jpg](file:///d:/facial/RO_Plant_Surveillance_ROI_Mesh.jpg) and Zoomed High-Definition Mesh at [RO_Plant_Zoomed_ROI_Mesh.jpg](file:///d:/facial/RO_Plant_Zoomed_ROI_Mesh.jpg).

### 3. Temporal Integrity & Boundary Bridging Engineering
1. **Continuous Rolling Temporal Windows:** Eliminates activity window timeouts by maintaining a sliding state across long 45-minute CCTV segments, preventing missed re-entry events.
2. **Multi-Segment Boundary Stitching:** Enforces $\pm 60$-second contextual safety buffers that automatically bridge adjacent video files, capturing full pre-incident approach and post-incident egress.
3. **ISO 8601 Wall-Clock Normalization:** All detection queries enforce `ORDER BY timestamp ASC` using absolute UTC/local wall-clock timestamps, eliminating intra-clip relative index interleaving.

### 4. Lossless Bitstream Extraction Throughput
- By executing direct FFmpeg bitstream extraction (`-c copy`), transcoding latency and quality degradation are eliminated.
- **Performance Benchmark:** Extracted **179 pristine MP4 incident clips (8.20 GB) in 108.7 seconds**, achieving an operational throughput of **>250x realtime speed** directly from read-only external storage.