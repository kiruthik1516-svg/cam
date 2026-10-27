# Forensic Biometric Directory: RO Water Treatment Plant
## 30-Day Discovered Identities, Behavioral Clusters & Equipment Integrity Ledger

### Document Control & Biometric Specification
| Parameter | Technical Specification |
| :--- | :--- |
| **Monitored Facility** | RO Water Treatment Plant Rooftop Deck | Camera `IPC56` |
| **Total Discovered Personas** | 1,652 Unknown Personas (`SUBJ-01` through `SUBJ-1652`) |
| **Biometric Model** | InsightFace ArcFace (512-Dimensional Normalized Embeddings) |
| **Clustering Threshold** | Unsupervised DBSCAN (Cosine Distance $\varepsilon \le 0.38$, Min Samples = 2) |
| **Quality Filtering** | Face Quality Score $Q \ge 40.0$, Detection Confidence $\ge 0.80$ |
| **Forensic Status** | 100% Unregistered Personnel (Pending Identity Verification & Formal Enrollment) |

---

### 1. Methodology & Identity Clustering Architecture
Facial vectors were extracted using InsightFace ArcFace from 36,226 high-quality candidate face crops ($Q \ge 40$). Recurring faces were grouped via unsupervised DBSCAN clustering using an analytical Euclidean mapping to cosine distance:

$$\varepsilon_{\text{euclidean}} = \sqrt{2 \cdot 0.38} \approx 0.87178$$

### 2. Tier 1 Master Directory: High-Frequency Recurring Unknown Subjects ($\ge 50$ Detections)
These 12 recurring unknown subjects represent the primary human presences on the rooftop:

| Subject ID | Forensic Status | Total Detections | Days Active | First Seen | Last Seen | Morning (A) | Afternoon (B) | Night (C) | Direct Contacts | Risk Level |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **SUBJ-01** | Unknown Subject (Pending Enrollment) | 29,598 | 29 | `2026-09-01 01:29:57` | `2026-09-30 23:32:16` | 20,793 | 8,481 | 324 | **116** | **CRITICAL** |
| **SUBJ-02** | Unknown Subject (Pending Enrollment) | 166 | 12 | `2026-09-01 09:04:02` | `2026-09-30 08:51:36` | 166 | 0 | 0 | **53** | **CRITICAL** |
| **SUBJ-03** | Unknown Subject (Pending Enrollment) | 104 | 2 | `2026-09-01 07:29:32` | `2026-09-11 07:46:44` | 104 | 0 | 0 | **0** | LOW |
| **SUBJ-04** | Unknown Subject (Pending Enrollment) | 87 | 16 | `2026-09-01 07:29:34` | `2026-09-30 08:13:33` | 87 | 0 | 0 | **0** | LOW |
| **SUBJ-05** | Unknown Subject (Pending Enrollment) | 86 | 2 | `2026-09-16 16:19:07` | `2026-09-23 11:21:56` | 85 | 1 | 0 | **0** | LOW |
| **SUBJ-06** | Unknown Subject (Pending Enrollment) | 85 | 12 | `2026-09-02 08:36:32` | `2026-09-30 09:14:55` | 85 | 0 | 0 | **0** | LOW |
| **SUBJ-07** | Unknown Subject (Pending Enrollment) | 81 | 3 | `2026-09-01 11:14:17` | `2026-09-21 11:22:46` | 81 | 0 | 0 | **0** | LOW |
| **SUBJ-08** | Unknown Subject (Pending Enrollment) | 79 | 10 | `2026-09-01 11:14:57` | `2026-09-29 11:14:42` | 30 | 49 | 0 | **0** | LOW |
| **SUBJ-09** | Unknown Subject (Pending Enrollment) | 79 | 1 | `2026-09-25 14:03:24` | `2026-09-25 14:15:57` | 0 | 79 | 0 | **0** | LOW |
| **SUBJ-10** | Unknown Subject (Pending Enrollment) | 75 | 2 | `2026-09-13 19:40:38` | `2026-09-21 19:37:46` | 0 | 75 | 0 | **0** | LOW |
| **SUBJ-11** | Unknown Subject (Pending Enrollment) | 69 | 9 | `2026-09-01 14:14:17` | `2026-09-30 09:13:37` | 44 | 25 | 0 | **0** | LOW |
| **SUBJ-12** | Unknown Subject (Pending Enrollment) | 68 | 2 | `2026-09-07 17:51:50` | `2026-09-09 17:50:37` | 0 | 68 | 0 | **0** | LOW |

### 3. Sighting Frequency Distribution (Tiers 1, 2, 3)
- **Tier 1 (High-Frequency Unknowns, $\ge 50$ Detections):** **12 individuals** (30,577 detections)
- **Tier 2 (Medium-Frequency Unknowns, $10 - 49$ Detections):** **85 individuals** (1,701 detections)
- **Tier 3 (Transient Unknowns, $2 - 9$ Detections):** **1,555 individuals** (3,948 detections)
- **Total Discovered Registry:** **1,652 individuals** (36,226 total detections)

### 4. Equipment Protection Zone Integrity Ledger (Direct Contact Audits)
Across the 30-day archive, exactly **18 unknown individuals** established verified direct physical contact ($\text{IoU} > 0.08$) with plant equipment assets:

| Subject ID | Total Contacts | Days Active | Total Detections | Primary Asset Contacted | Hazard Rating | Operational Action |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **SUBJ-01** | **116 contacts** | 29 | 29598 | Two Multiport Backwash Valves | **CRITICAL** | Physical operation & valve manipulation |
| **SUBJ-02** | **53 contacts** | 12 | 166 | RO Skid Controls & Walkway | **ELEVATED** | Physical operation & valve manipulation |
| **SUBJ-102** | **5 contacts** | 1 | 8 | RO Skid Controls & Walkway | **ELEVATED** | Physical operation & valve manipulation |
| **SUBJ-167** | **5 contacts** | 1 | 6 | RO Skid Controls & Walkway | **ELEVATED** | Physical operation & valve manipulation |
| **SUBJ-41** | **4 contacts** | 10 | 20 | RO Skid Controls & Walkway | **ELEVATED** | Physical operation & valve manipulation |
| **SUBJ-344** | **3 contacts** | 1 | 3 | RO Skid Controls & Walkway | **ELEVATED** | Physical operation & valve manipulation |
| **SUBJ-395** | **3 contacts** | 1 | 3 | RO Skid Controls & Walkway | **ELEVATED** | Physical operation & valve manipulation |
| **SUBJ-129** | **2 contacts** | 1 | 7 | RO Skid Controls & Walkway | **ELEVATED** | Physical operation & valve manipulation |
| **SUBJ-489** | **2 contacts** | 1 | 2 | RO Skid Controls & Walkway | **ELEVATED** | Physical operation & valve manipulation |
| **SUBJ-22** | **1 contacts** | 1 | 35 | RO Skid Controls & Walkway | **ELEVATED** | Physical operation & valve manipulation |
| **SUBJ-1652** | **1 contacts** | 1 | 28 | Two Multiport Backwash Valves | **CRITICAL** | Physical operation & valve manipulation |
| **SUBJ-342** | **1 contacts** | 1 | 3 | RO Skid Controls & Walkway | **ELEVATED** | Physical operation & valve manipulation |
| **SUBJ-582** | **1 contacts** | 1 | 2 | RO Skid Controls & Walkway | **ELEVATED** | Physical operation & valve manipulation |
| **SUBJ-759** | **1 contacts** | 1 | 2 | Ultimate Plant Power Switch | **SEVERE** | Physical operation & valve manipulation |
| **SUBJ-842** | **1 contacts** | 1 | 2 | RO Skid Controls & Walkway | **ELEVATED** | Physical operation & valve manipulation |
| **SUBJ-890** | **1 contacts** | 1 | 2 | Two Multiport Backwash Valves | **CRITICAL** | Physical operation & valve manipulation |
| **SUBJ-993** | **1 contacts** | 1 | 2 | RO Skid Controls & Walkway | **ELEVATED** | Physical operation & valve manipulation |
| **SUBJ-1079** | **1 contacts** | 1 | 2 | Ultimate Plant Power Switch | **SEVERE** | Physical operation & valve manipulation |

### 5. Comparative Forensic Analysis: Unknown Subject SUBJ-1652 vs SUBJ-02
High-resolution facial feature analysis confirmed that the unknown individual observed operating the multiport valve on Day 1 at `09:53:38` is **distinct from `SUBJ-02`**:

| Biometric Attribute | Unknown Subject `SUBJ-02` (09:04:32) | Unknown Subject `SUBJ-1652` (09:53:38) | Forensic Comparison Verdict |
| :--- | :--- | :--- | :--- |
| **Portrait Reference** | [`SUBJ-02_exemplar.jpg`](file:///d:/facial/data/30day_personas/portraits/SUBJ-02_exemplar.jpg) | [`SUBJ-1652_exemplar.jpg`](file:///d:/facial/data/30day_personas/portraits/SUBJ-1652_exemplar.jpg) | Two visually distinct individuals |
| **ArcFace 512-D Cosine Sim** | Baseline | **`0.1831`** | **NON-MATCH** (Match threshold $\ge 0.4500$) |
| **Normalized Correlation** | Baseline | **`0.0434`** | **Zero pixel-level correlation** |
| **Attire & Visuals** | Dark Navy / Black Shirt | **Teal / Green Polo Shirt** | Distinct civilian/work attire |
| **Hairstyle & Features** | Straight parted hair, slim jaw | Curly thick hair, mustache & goatee | Distinct age and facial morphology |
| **Incident Clip** | `EVT-D01-003` (09:03:18) | [`Day01_0953_Manual_Incident_Audit.mp4`](file:///d:/facial/incident_evidence/day_01/Day01_0953_Manual_Incident_Audit.mp4) | Verified independent morning access |

Side-by-side photographic evidence is available at [side_by_side_comparison.jpg](file:///d:/facial/side_by_side_comparison.jpg).