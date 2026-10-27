# RO Water Treatment Plant: Forensic Biometrics & Master Persona Directory
## 30-Day Discovered Identities, Behavioral Clusters & Equipment Integrity Ledger

> [!NOTE]
> **Target Location:** RO Water Treatment Plant Rooftop | Camera `IPC56`  
> **Discovered Registry:** 1,652 Unique Personas (`SUBJ-01` to `SUBJ-1652`)  
> **Clustering Criteria:** DBSCAN Unsupervised Cosine Clustering (Cosine $\varepsilon \le 0.38$, Min Samples = 2)  
> **Target Audience:** Security Directors, Identity Analysts, and Biometric Auditing Teams  

---

### 1. Methodology & Identity Clustering Architecture
Facial vectors were extracted using InsightFace ArcFace (512-dimensional normalized float embeddings) from 36,198 high-quality candidate face crops ($Q \ge 40$). Recurring faces were grouped via unsupervised DBSCAN clustering using an analytical Euclidean mapping to cosine distance:

$$\varepsilon_{\text{euclidean}} = \sqrt{2 \cdot 0.38} \approx 0.87178$$

### 2. Tier 1: Core Operational Staff ($\ge 50$ Detections)
| Subject ID | Status / Role | Total Dets | Days Active | First Seen | Last Seen | Morning (A) | Afternoon (B) | Night (C) | Equipment Contacts | Risk Assessment |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **SUBJ-01** | Core RO Plant Technician | 29,598 | 29 | `2026-09-01 01:29:57` | `2026-09-30 23:32:16` | 20,793 | 8,481 | 324 | **116** | **CRITICAL** |
| **SUBJ-02** | Core RO Plant Technician | 166 | 12 | `2026-09-01 09:04:02` | `2026-09-30 08:51:36` | 166 | 0 | 0 | **53** | **CRITICAL** |
| **SUBJ-03** | Core RO Plant Technician | 104 | 2 | `2026-09-01 07:29:32` | `2026-09-11 07:46:44` | 104 | 0 | 0 | **0** | LOW |
| **SUBJ-04** | Core RO Plant Technician | 87 | 16 | `2026-09-01 07:29:34` | `2026-09-30 08:13:33` | 87 | 0 | 0 | **0** | LOW |
| **SUBJ-05** | Core RO Plant Technician | 86 | 2 | `2026-09-16 16:19:07` | `2026-09-23 11:21:56` | 85 | 1 | 0 | **0** | LOW |
| **SUBJ-06** | Core RO Plant Technician | 85 | 12 | `2026-09-02 08:36:32` | `2026-09-30 09:14:55` | 85 | 0 | 0 | **0** | LOW |
| **SUBJ-07** | Core RO Plant Technician | 81 | 3 | `2026-09-01 11:14:17` | `2026-09-21 11:22:46` | 81 | 0 | 0 | **0** | LOW |
| **SUBJ-08** | Core RO Plant Technician | 79 | 10 | `2026-09-01 11:14:57` | `2026-09-29 11:14:42` | 30 | 49 | 0 | **0** | LOW |
| **SUBJ-09** | Core RO Plant Technician | 79 | 1 | `2026-09-25 14:03:24` | `2026-09-25 14:15:57` | 0 | 79 | 0 | **0** | LOW |
| **SUBJ-10** | Core RO Plant Technician | 75 | 2 | `2026-09-13 19:40:38` | `2026-09-21 19:37:46` | 0 | 75 | 0 | **0** | LOW |
| **SUBJ-11** | Core RO Plant Technician | 69 | 9 | `2026-09-01 14:14:17` | `2026-09-30 09:13:37` | 44 | 25 | 0 | **0** | LOW |
| **SUBJ-12** | Core RO Plant Technician | 68 | 2 | `2026-09-07 17:51:50` | `2026-09-09 17:50:37` | 0 | 68 | 0 | **0** | LOW |

### 3. Equipment Protection Zone Integrity Ledger (Direct Contact Audits)
Across 30 days, exactly **17 individuals** established verified direct physical contact ($\text{IoU} > 0.08$) with plant equipment assets:

| Subject ID | Total Contacts | Days Active | Total Detections | Primary Asset Contacted | Hazard Rating | Operational Action |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **SUBJ-01** | **116 contacts** | 29 days | 29598 | Two Multiport Backwash Valves | **CRITICAL** | Physical operation & valve manipulation |
| **SUBJ-02** | **53 contacts** | 12 days | 166 | RO Skid Controls & Walkway | **ELEVATED** | Physical operation & valve manipulation |
| **SUBJ-102** | **5 contacts** | 1 days | 8 | RO Skid Controls & Walkway | **ELEVATED** | Physical operation & valve manipulation |
| **SUBJ-167** | **5 contacts** | 1 days | 6 | RO Skid Controls & Walkway | **ELEVATED** | Physical operation & valve manipulation |
| **SUBJ-41** | **4 contacts** | 10 days | 20 | RO Skid Controls & Walkway | **ELEVATED** | Physical operation & valve manipulation |
| **SUBJ-344** | **3 contacts** | 1 days | 3 | RO Skid Controls & Walkway | **ELEVATED** | Physical operation & valve manipulation |
| **SUBJ-395** | **3 contacts** | 1 days | 3 | RO Skid Controls & Walkway | **ELEVATED** | Physical operation & valve manipulation |
| **SUBJ-129** | **2 contacts** | 1 days | 7 | RO Skid Controls & Walkway | **ELEVATED** | Physical operation & valve manipulation |
| **SUBJ-489** | **2 contacts** | 1 days | 2 | RO Skid Controls & Walkway | **ELEVATED** | Physical operation & valve manipulation |
| **SUBJ-22** | **1 contacts** | 1 days | 35 | RO Skid Controls & Walkway | **ELEVATED** | Physical operation & valve manipulation |
| **SUBJ-1652** | **1 contacts** | 1 days | 28 | Two Multiport Backwash Valves | **CRITICAL** | Physical operation & valve manipulation |
| **SUBJ-342** | **1 contacts** | 1 days | 3 | RO Skid Controls & Walkway | **ELEVATED** | Physical operation & valve manipulation |
| **SUBJ-582** | **1 contacts** | 1 days | 2 | RO Skid Controls & Walkway | **ELEVATED** | Physical operation & valve manipulation |
| **SUBJ-759** | **1 contacts** | 1 days | 2 | Ultimate Plant Power Switch | **SEVERE** | Physical operation & valve manipulation |
| **SUBJ-842** | **1 contacts** | 1 days | 2 | RO Skid Controls & Walkway | **ELEVATED** | Physical operation & valve manipulation |
| **SUBJ-890** | **1 contacts** | 1 days | 2 | Two Multiport Backwash Valves | **CRITICAL** | Physical operation & valve manipulation |
| **SUBJ-993** | **1 contacts** | 1 days | 2 | RO Skid Controls & Walkway | **ELEVATED** | Physical operation & valve manipulation |
| **SUBJ-1079** | **1 contacts** | 1 days | 2 | Ultimate Plant Power Switch | **SEVERE** | Physical operation & valve manipulation |

### 4. Special Forensic Investigation: Operator SUBJ-1652 vs SUBJ-02
> [!IMPORTANT]
> **Biometric Ground Truth Verification:**  
> Detailed manual inspection on Day 1 at `09:53:38` isolated an operator manually turning the yellow multiport backwash valve. A comparative analysis proved that this operator is **NOT** `SUBJ-02`:

| Biometric Attribute | Official `SUBJ-02` (09:04:32) | Recovered Operator `SUBJ-1652` (09:53:38) | Forensic Comparison Verdict |
| :--- | :--- | :--- | :--- |
| **Portrait Reference** | [`SUBJ-02_exemplar.jpg`](file:///d:/facial/data/30day_personas/portraits/SUBJ-02_exemplar.jpg) | [`SUBJ-1652_exemplar.jpg`](file:///d:/facial/data/30day_personas/portraits/SUBJ-1652_exemplar.jpg) | Two visually distinct faces |
| **ArcFace 512-D Cosine Sim** | Baseline | **`0.1831`** | **NON-MATCH** (Match threshold $\ge 0.4500$) |
| **Normalized Correlation** | Baseline | **`0.0434`** | **Zero pixel-level correlation** |
| **Attire & Visuals** | Dark Navy / Black Shirt | **Teal / Green Polo Shirt** | Distinct shift worker uniforms |
| **Hairstyle & Features** | Straight parted hair, slim jaw | Curly thick hair, mustache & goatee | Distinct age and facial morphology |
| **Incident Clip** | `EVT-D01-003` (09:03:18) | [`Day01_0953_Manual_Incident_Audit.mp4`](file:///d:/facial/incident_evidence/day_01/Day01_0953_Manual_Incident_Audit.mp4) | Verified independent morning access |

Side-by-side photographic proof is compiled in [side_by_side_comparison.jpg](file:///d:/facial/side_by_side_comparison.jpg).