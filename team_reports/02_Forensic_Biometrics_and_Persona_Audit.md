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

### 2. Population Sighting Frequency Distribution
All 1,652 discovered unknown personas are categorized into three statistical recurrence tiers:
- **Tier 1 (High-Frequency Unknowns, $\ge 50$ Detections):** **12 individuals** (30,577 detections, 9.4% of total volume). Routine rooftop presence.
- **Tier 2 (Medium-Frequency Unknowns, $10 - 49$ Detections):** **85 individuals** (1,701 detections, 5.9% of total volume). Periodic rooftop visitors.
- **Tier 3 (Transient Unknowns, $2 - 9$ Detections):** **1,555 individuals** (3,948 detections, 84.7% of total volume). Short-duration or single-visit presences.
- **Total Discovered Registry:** **1,652 individuals** (36,226 total face detections across 30 days).

---

### 3. Equipment Protection Zone Integrity Ledger (All 18 Unknown Contact Breaches)
Across the 30-day archive, exactly **18 unique unknown individuals** established verified direct physical contact ($\text{IoU} > 0.08$) with plant equipment assets:

| Subject ID | Total Contacts | Active Days | Total Detections | First Seen | Last Seen | Primary Asset Contacted | Hazard Rating | Operational Action |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **SUBJ-01** | **116 contacts** | 29 | 29598 | `2026-09-01` | `2026-09-30` | Two Multiport Backwash Valves | **CRITICAL** | Physical operation & valve manipulation |
| **SUBJ-02** | **53 contacts** | 12 | 166 | `2026-09-01` | `2026-09-30` | RO Skid Controls & Walkway | **ELEVATED** | Physical operation & valve manipulation |
| **SUBJ-102** | **5 contacts** | 1 | 8 | `2026-09-02` | `2026-09-02` | RO Skid Controls & Walkway | **ELEVATED** | Physical operation & valve manipulation |
| **SUBJ-167** | **5 contacts** | 1 | 6 | `2026-09-25` | `2026-09-25` | RO Skid Controls & Walkway | **ELEVATED** | Physical operation & valve manipulation |
| **SUBJ-41** | **4 contacts** | 10 | 20 | `2026-09-03` | `2026-09-24` | RO Skid Controls & Walkway | **ELEVATED** | Physical operation & valve manipulation |
| **SUBJ-344** | **3 contacts** | 1 | 3 | `2026-09-09` | `2026-09-09` | RO Skid Controls & Walkway | **ELEVATED** | Physical operation & valve manipulation |
| **SUBJ-395** | **3 contacts** | 1 | 3 | `2026-09-16` | `2026-09-16` | RO Skid Controls & Walkway | **ELEVATED** | Physical operation & valve manipulation |
| **SUBJ-129** | **2 contacts** | 1 | 7 | `2026-09-06` | `2026-09-06` | RO Skid Controls & Walkway | **ELEVATED** | Physical operation & valve manipulation |
| **SUBJ-489** | **2 contacts** | 1 | 2 | `2026-09-01` | `2026-09-01` | RO Skid Controls & Walkway | **ELEVATED** | Physical operation & valve manipulation |
| **SUBJ-22** | **1 contacts** | 1 | 35 | `2026-09-19` | `2026-09-19` | RO Skid Controls & Walkway | **ELEVATED** | Physical operation & valve manipulation |
| **SUBJ-1652** | **1 contacts** | 1 | 28 | `2026-09-01` | `2026-09-01` | Two Multiport Backwash Valves | **CRITICAL** | Physical operation & valve manipulation |
| **SUBJ-342** | **1 contacts** | 1 | 3 | `2026-09-09` | `2026-09-09` | RO Skid Controls & Walkway | **ELEVATED** | Physical operation & valve manipulation |
| **SUBJ-582** | **1 contacts** | 1 | 2 | `2026-09-02` | `2026-09-02` | RO Skid Controls & Walkway | **ELEVATED** | Physical operation & valve manipulation |
| **SUBJ-759** | **1 contacts** | 1 | 2 | `2026-09-09` | `2026-09-09` | Ultimate Plant Power Switch | **SEVERE** | Physical operation & valve manipulation |
| **SUBJ-842** | **1 contacts** | 1 | 2 | `2026-09-13` | `2026-09-13` | RO Skid Controls & Walkway | **ELEVATED** | Physical operation & valve manipulation |
| **SUBJ-890** | **1 contacts** | 1 | 2 | `2026-09-15` | `2026-09-15` | Two Multiport Backwash Valves | **CRITICAL** | Physical operation & valve manipulation |
| **SUBJ-993** | **1 contacts** | 1 | 2 | `2026-09-19` | `2026-09-19` | RO Skid Controls & Walkway | **ELEVATED** | Physical operation & valve manipulation |
| **SUBJ-1079** | **1 contacts** | 1 | 2 | `2026-09-24` | `2026-09-24` | Ultimate Plant Power Switch | **SEVERE** | Physical operation & valve manipulation |

---

### 4. Master Directory of Recurring Unknown Subjects (All 97 Tier 1 & Tier 2 Individuals)
The directory below catalogs every one of the **97 recurring unknown individuals** with 10 or more confirmed facial detections across the 30-day surveillance window:

| Rank | Subject ID | Sighting Tier | Total Dets | Days Active | First Seen | Last Seen | Morning (A) | Afternoon (B) | Night (C) | Contacts | Risk Assessment |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | **SUBJ-01** | Tier 1 (High-Freq) | 29,598 | 29 | `2026-09-01 01:29` | `2026-09-30 23:32` | 20,793 | 8,481 | 324 | **116** | **CRITICAL** |
| 2 | **SUBJ-02** | Tier 1 (High-Freq) | 166 | 12 | `2026-09-01 09:04` | `2026-09-30 08:51` | 166 | 0 | 0 | **53** | **CRITICAL** |
| 3 | **SUBJ-03** | Tier 1 (High-Freq) | 104 | 2 | `2026-09-01 07:29` | `2026-09-11 07:46` | 104 | 0 | 0 | 0 | LOW |
| 4 | **SUBJ-04** | Tier 1 (High-Freq) | 87 | 16 | `2026-09-01 07:29` | `2026-09-30 08:13` | 87 | 0 | 0 | 0 | LOW |
| 5 | **SUBJ-05** | Tier 1 (High-Freq) | 86 | 2 | `2026-09-16 16:19` | `2026-09-23 11:21` | 85 | 1 | 0 | 0 | LOW |
| 6 | **SUBJ-06** | Tier 1 (High-Freq) | 85 | 12 | `2026-09-02 08:36` | `2026-09-30 09:14` | 85 | 0 | 0 | 0 | LOW |
| 7 | **SUBJ-07** | Tier 1 (High-Freq) | 81 | 3 | `2026-09-01 11:14` | `2026-09-21 11:22` | 81 | 0 | 0 | 0 | LOW |
| 8 | **SUBJ-08** | Tier 1 (High-Freq) | 79 | 10 | `2026-09-01 11:14` | `2026-09-29 11:14` | 30 | 49 | 0 | 0 | LOW |
| 9 | **SUBJ-09** | Tier 1 (High-Freq) | 79 | 1 | `2026-09-25 14:03` | `2026-09-25 14:15` | 0 | 79 | 0 | 0 | LOW |
| 10 | **SUBJ-10** | Tier 1 (High-Freq) | 75 | 2 | `2026-09-13 19:40` | `2026-09-21 19:37` | 0 | 75 | 0 | 0 | LOW |
| 11 | **SUBJ-11** | Tier 1 (High-Freq) | 69 | 9 | `2026-09-01 14:14` | `2026-09-30 09:13` | 44 | 25 | 0 | 0 | LOW |
| 12 | **SUBJ-12** | Tier 1 (High-Freq) | 68 | 2 | `2026-09-07 17:51` | `2026-09-09 17:50` | 0 | 68 | 0 | 0 | LOW |
| 13 | **SUBJ-13** | Tier 2 (Periodic) | 47 | 5 | `2026-09-03 11:56` | `2026-09-30 11:12` | 29 | 18 | 0 | 0 | LOW |
| 14 | **SUBJ-14** | Tier 2 (Periodic) | 46 | 1 | `2026-09-16 07:44` | `2026-09-16 07:46` | 46 | 0 | 0 | 0 | LOW |
| 15 | **SUBJ-15** | Tier 2 (Periodic) | 46 | 1 | `2026-09-26 16:16` | `2026-09-26 16:18` | 0 | 46 | 0 | 0 | LOW |
| 16 | **SUBJ-16** | Tier 2 (Periodic) | 44 | 8 | `2026-09-01 11:14` | `2026-09-25 16:27` | 32 | 12 | 0 | 0 | LOW |
| 17 | **SUBJ-17** | Tier 2 (Periodic) | 43 | 3 | `2026-09-05 17:52` | `2026-09-19 17:20` | 0 | 43 | 0 | 0 | LOW |
| 18 | **SUBJ-18** | Tier 2 (Periodic) | 41 | 2 | `2026-09-18 11:15` | `2026-09-23 17:08` | 9 | 32 | 0 | 0 | LOW |
| 19 | **SUBJ-19** | Tier 2 (Periodic) | 39 | 2 | `2026-09-09 17:48` | `2026-09-26 17:46` | 0 | 39 | 0 | 0 | LOW |
| 20 | **SUBJ-20** | Tier 2 (Periodic) | 37 | 1 | `2026-09-18 08:11` | `2026-09-18 08:12` | 37 | 0 | 0 | 0 | LOW |
| 21 | **SUBJ-21** | Tier 2 (Periodic) | 36 | 1 | `2026-09-07 11:25` | `2026-09-07 11:27` | 36 | 0 | 0 | 0 | LOW |
| 22 | **SUBJ-22** | Tier 2 (Periodic) | 35 | 1 | `2026-09-19 16:55` | `2026-09-19 17:52` | 0 | 35 | 0 | **1** | **ELEVATED** |
| 23 | **SUBJ-23** | Tier 2 (Periodic) | 33 | 2 | `2026-09-08 17:54` | `2026-09-19 17:14` | 0 | 33 | 0 | 0 | LOW |
| 24 | **SUBJ-24** | Tier 2 (Periodic) | 32 | 1 | `2026-09-01 15:43` | `2026-09-01 15:44` | 0 | 32 | 0 | 0 | LOW |
| 25 | **SUBJ-25** | Tier 2 (Periodic) | 29 | 9 | `2026-09-03 06:30` | `2026-09-30 07:06` | 29 | 0 | 0 | 0 | LOW |
| 26 | **SUBJ-26** | Tier 2 (Periodic) | 28 | 1 | `2026-09-03 13:08` | `2026-09-03 13:22` | 28 | 0 | 0 | 0 | LOW |
| 27 | **SUBJ-27** | Tier 2 (Periodic) | 28 | 2 | `2026-09-08 17:53` | `2026-09-19 17:10` | 0 | 28 | 0 | 0 | LOW |
| 28 | **SUBJ-1652** | Tier 2 (Periodic) | 28 | 1 | `2026-09-01 09:53` | `2026-09-01 09:54` | 28 | 0 | 0 | **1** | **ELEVATED** |
| 29 | **SUBJ-28** | Tier 2 (Periodic) | 27 | 3 | `2026-09-08 17:15` | `2026-09-15 14:50` | 1 | 26 | 0 | 0 | LOW |
| 30 | **SUBJ-29** | Tier 2 (Periodic) | 27 | 1 | `2026-09-29 17:14` | `2026-09-29 17:15` | 0 | 27 | 0 | 0 | LOW |
| 31 | **SUBJ-30** | Tier 2 (Periodic) | 26 | 1 | `2026-09-02 16:50` | `2026-09-02 16:53` | 0 | 26 | 0 | 0 | LOW |
| 32 | **SUBJ-31** | Tier 2 (Periodic) | 26 | 1 | `2026-09-03 16:40` | `2026-09-03 16:41` | 0 | 26 | 0 | 0 | LOW |
| 33 | **SUBJ-32** | Tier 2 (Periodic) | 25 | 1 | `2026-09-24 16:24` | `2026-09-24 16:25` | 0 | 25 | 0 | 0 | LOW |
| 34 | **SUBJ-33** | Tier 2 (Periodic) | 23 | 6 | `2026-09-01 11:14` | `2026-09-24 16:23` | 16 | 7 | 0 | 0 | LOW |
| 35 | **SUBJ-34** | Tier 2 (Periodic) | 23 | 1 | `2026-09-18 17:25` | `2026-09-18 17:26` | 0 | 23 | 0 | 0 | LOW |
| 36 | **SUBJ-35** | Tier 2 (Periodic) | 23 | 1 | `2026-09-22 11:05` | `2026-09-22 11:06` | 23 | 0 | 0 | 0 | LOW |
| 37 | **SUBJ-36** | Tier 2 (Periodic) | 22 | 1 | `2026-09-26 17:45` | `2026-09-26 17:47` | 0 | 22 | 0 | 0 | LOW |
| 38 | **SUBJ-37** | Tier 2 (Periodic) | 22 | 1 | `2026-09-29 12:49` | `2026-09-29 12:50` | 22 | 0 | 0 | 0 | LOW |
| 39 | **SUBJ-38** | Tier 2 (Periodic) | 21 | 10 | `2026-09-02 08:09` | `2026-09-28 09:06` | 21 | 0 | 0 | 0 | LOW |
| 40 | **SUBJ-39** | Tier 2 (Periodic) | 21 | 1 | `2026-09-02 09:53` | `2026-09-02 10:02` | 21 | 0 | 0 | 0 | LOW |
| 41 | **SUBJ-40** | Tier 2 (Periodic) | 21 | 1 | `2026-09-24 07:44` | `2026-09-24 07:45` | 21 | 0 | 0 | 0 | LOW |
| 42 | **SUBJ-41** | Tier 2 (Periodic) | 20 | 10 | `2026-09-03 11:31` | `2026-09-24 16:27` | 8 | 12 | 0 | **4** | **ELEVATED** |
| 43 | **SUBJ-42** | Tier 2 (Periodic) | 20 | 1 | `2026-09-07 11:22` | `2026-09-07 11:23` | 20 | 0 | 0 | 0 | LOW |
| 44 | **SUBJ-43** | Tier 2 (Periodic) | 20 | 1 | `2026-09-07 16:59` | `2026-09-07 17:00` | 0 | 20 | 0 | 0 | LOW |
| 45 | **SUBJ-44** | Tier 2 (Periodic) | 20 | 2 | `2026-09-09 16:21` | `2026-09-11 16:27` | 0 | 20 | 0 | 0 | LOW |
| 46 | **SUBJ-45** | Tier 2 (Periodic) | 20 | 1 | `2026-09-18 16:38` | `2026-09-18 16:38` | 0 | 20 | 0 | 0 | LOW |
| 47 | **SUBJ-46** | Tier 2 (Periodic) | 20 | 1 | `2026-09-26 17:43` | `2026-09-26 17:43` | 0 | 20 | 0 | 0 | LOW |
| 48 | **SUBJ-47** | Tier 2 (Periodic) | 19 | 2 | `2026-09-02 07:44` | `2026-09-16 07:43` | 19 | 0 | 0 | 0 | LOW |
| 49 | **SUBJ-48** | Tier 2 (Periodic) | 19 | 1 | `2026-09-06 08:02` | `2026-09-06 08:02` | 19 | 0 | 0 | 0 | LOW |
| 50 | **SUBJ-49** | Tier 2 (Periodic) | 19 | 1 | `2026-09-07 11:25` | `2026-09-07 11:26` | 19 | 0 | 0 | 0 | LOW |
| 51 | **SUBJ-50** | Tier 2 (Periodic) | 19 | 1 | `2026-09-17 16:30` | `2026-09-17 16:31` | 0 | 19 | 0 | 0 | LOW |
| 52 | **SUBJ-51** | Tier 2 (Periodic) | 19 | 1 | `2026-09-29 12:48` | `2026-09-29 12:52` | 19 | 0 | 0 | 0 | LOW |
| 53 | **SUBJ-52** | Tier 2 (Periodic) | 18 | 1 | `2026-09-13 19:17` | `2026-09-13 19:18` | 0 | 18 | 0 | 0 | LOW |
| 54 | **SUBJ-53** | Tier 2 (Periodic) | 18 | 1 | `2026-09-18 16:39` | `2026-09-18 16:39` | 0 | 18 | 0 | 0 | LOW |
| 55 | **SUBJ-54** | Tier 2 (Periodic) | 18 | 1 | `2026-09-26 16:20` | `2026-09-26 16:21` | 0 | 18 | 0 | 0 | LOW |
| 56 | **SUBJ-55** | Tier 2 (Periodic) | 17 | 1 | `2026-09-16 07:41` | `2026-09-16 07:41` | 17 | 0 | 0 | 0 | LOW |
| 57 | **SUBJ-56** | Tier 2 (Periodic) | 17 | 1 | `2026-09-16 16:22` | `2026-09-16 16:23` | 0 | 17 | 0 | 0 | LOW |
| 58 | **SUBJ-57** | Tier 2 (Periodic) | 17 | 1 | `2026-09-21 10:11` | `2026-09-21 10:20` | 17 | 0 | 0 | 0 | LOW |
| 59 | **SUBJ-58** | Tier 2 (Periodic) | 16 | 1 | `2026-09-04 11:03` | `2026-09-04 11:03` | 16 | 0 | 0 | 0 | LOW |
| 60 | **SUBJ-59** | Tier 2 (Periodic) | 16 | 1 | `2026-09-13 19:17` | `2026-09-13 19:17` | 0 | 16 | 0 | 0 | LOW |
| 61 | **SUBJ-60** | Tier 2 (Periodic) | 15 | 1 | `2026-09-05 08:12` | `2026-09-05 08:12` | 15 | 0 | 0 | 0 | LOW |
| 62 | **SUBJ-61** | Tier 2 (Periodic) | 15 | 1 | `2026-09-08 11:29` | `2026-09-08 11:29` | 15 | 0 | 0 | 0 | LOW |
| 63 | **SUBJ-62** | Tier 2 (Periodic) | 15 | 1 | `2026-09-15 09:21` | `2026-09-15 09:28` | 15 | 0 | 0 | 0 | LOW |
| 64 | **SUBJ-63** | Tier 2 (Periodic) | 15 | 1 | `2026-09-16 07:51` | `2026-09-16 07:51` | 15 | 0 | 0 | 0 | LOW |
| 65 | **SUBJ-64** | Tier 2 (Periodic) | 15 | 4 | `2026-09-17 11:07` | `2026-09-25 16:13` | 3 | 12 | 0 | 0 | LOW |
| 66 | **SUBJ-65** | Tier 2 (Periodic) | 15 | 1 | `2026-09-20 17:43` | `2026-09-20 17:44` | 0 | 15 | 0 | 0 | LOW |
| 67 | **SUBJ-66** | Tier 2 (Periodic) | 14 | 3 | `2026-09-01 16:29` | `2026-09-25 16:32` | 0 | 14 | 0 | 0 | LOW |
| 68 | **SUBJ-67** | Tier 2 (Periodic) | 14 | 1 | `2026-09-02 13:49` | `2026-09-02 13:50` | 14 | 0 | 0 | 0 | LOW |
| 69 | **SUBJ-68** | Tier 2 (Periodic) | 14 | 1 | `2026-09-03 06:09` | `2026-09-03 06:09` | 14 | 0 | 0 | 0 | LOW |
| 70 | **SUBJ-69** | Tier 2 (Periodic) | 14 | 1 | `2026-09-07 16:34` | `2026-09-07 16:34` | 0 | 14 | 0 | 0 | LOW |
| 71 | **SUBJ-70** | Tier 2 (Periodic) | 14 | 1 | `2026-09-11 09:41` | `2026-09-11 09:43` | 14 | 0 | 0 | 0 | LOW |
| 72 | **SUBJ-71** | Tier 2 (Periodic) | 14 | 1 | `2026-09-11 10:09` | `2026-09-11 10:09` | 14 | 0 | 0 | 0 | LOW |
| 73 | **SUBJ-72** | Tier 2 (Periodic) | 14 | 1 | `2026-09-26 17:45` | `2026-09-26 17:45` | 0 | 14 | 0 | 0 | LOW |
| 74 | **SUBJ-73** | Tier 2 (Periodic) | 13 | 3 | `2026-09-04 07:34` | `2026-09-30 07:48` | 13 | 0 | 0 | 0 | LOW |
| 75 | **SUBJ-74** | Tier 2 (Periodic) | 13 | 1 | `2026-09-11 09:50` | `2026-09-11 09:51` | 13 | 0 | 0 | 0 | LOW |
| 76 | **SUBJ-75** | Tier 2 (Periodic) | 13 | 1 | `2026-09-15 17:46` | `2026-09-15 17:46` | 0 | 13 | 0 | 0 | LOW |
| 77 | **SUBJ-76** | Tier 2 (Periodic) | 12 | 1 | `2026-09-01 16:29` | `2026-09-01 16:29` | 0 | 12 | 0 | 0 | LOW |
| 78 | **SUBJ-77** | Tier 2 (Periodic) | 12 | 6 | `2026-09-07 11:28` | `2026-09-28 11:20` | 11 | 1 | 0 | 0 | LOW |
| 79 | **SUBJ-78** | Tier 2 (Periodic) | 12 | 1 | `2026-09-23 11:22` | `2026-09-23 11:23` | 12 | 0 | 0 | 0 | LOW |
| 80 | **SUBJ-79** | Tier 2 (Periodic) | 12 | 1 | `2026-09-23 11:28` | `2026-09-23 11:28` | 12 | 0 | 0 | 0 | LOW |
| 81 | **SUBJ-80** | Tier 2 (Periodic) | 11 | 1 | `2026-09-02 09:45` | `2026-09-02 09:46` | 11 | 0 | 0 | 0 | LOW |
| 82 | **SUBJ-81** | Tier 2 (Periodic) | 11 | 1 | `2026-09-03 06:33` | `2026-09-03 06:34` | 11 | 0 | 0 | 0 | LOW |
| 83 | **SUBJ-82** | Tier 2 (Periodic) | 11 | 2 | `2026-09-03 07:29` | `2026-09-10 07:36` | 11 | 0 | 0 | 0 | LOW |
| 84 | **SUBJ-83** | Tier 2 (Periodic) | 11 | 4 | `2026-09-06 07:35` | `2026-09-26 07:48` | 11 | 0 | 0 | 0 | LOW |
| 85 | **SUBJ-84** | Tier 2 (Periodic) | 11 | 1 | `2026-09-18 14:36` | `2026-09-18 14:36` | 0 | 11 | 0 | 0 | LOW |
| 86 | **SUBJ-85** | Tier 2 (Periodic) | 10 | 2 | `2026-09-01 16:29` | `2026-09-22 11:26` | 4 | 6 | 0 | 0 | LOW |
| 87 | **SUBJ-86** | Tier 2 (Periodic) | 10 | 3 | `2026-09-01 16:29` | `2026-09-11 16:47` | 0 | 10 | 0 | 0 | LOW |
| 88 | **SUBJ-87** | Tier 2 (Periodic) | 10 | 6 | `2026-09-02 07:36` | `2026-09-28 08:48` | 10 | 0 | 0 | 0 | LOW |
| 89 | **SUBJ-88** | Tier 2 (Periodic) | 10 | 2 | `2026-09-03 07:29` | `2026-09-23 07:46` | 10 | 0 | 0 | 0 | LOW |
| 90 | **SUBJ-89** | Tier 2 (Periodic) | 10 | 2 | `2026-09-04 07:33` | `2026-09-06 08:55` | 10 | 0 | 0 | 0 | LOW |
| 91 | **SUBJ-90** | Tier 2 (Periodic) | 10 | 6 | `2026-09-04 08:06` | `2026-09-19 12:01` | 10 | 0 | 0 | 0 | LOW |
| 92 | **SUBJ-91** | Tier 2 (Periodic) | 10 | 1 | `2026-09-07 11:25` | `2026-09-07 11:27` | 10 | 0 | 0 | 0 | LOW |
| 93 | **SUBJ-92** | Tier 2 (Periodic) | 10 | 3 | `2026-09-09 16:25` | `2026-09-25 17:27` | 0 | 10 | 0 | 0 | LOW |
| 94 | **SUBJ-93** | Tier 2 (Periodic) | 10 | 1 | `2026-09-14 09:56` | `2026-09-14 09:56` | 10 | 0 | 0 | 0 | LOW |
| 95 | **SUBJ-94** | Tier 2 (Periodic) | 10 | 3 | `2026-09-22 14:04` | `2026-09-26 16:22` | 0 | 10 | 0 | 0 | LOW |
| 96 | **SUBJ-95** | Tier 2 (Periodic) | 10 | 1 | `2026-09-26 17:46` | `2026-09-26 17:46` | 0 | 10 | 0 | 0 | LOW |
| 97 | **SUBJ-96** | Tier 2 (Periodic) | 10 | 1 | `2026-09-29 12:48` | `2026-09-29 12:49` | 10 | 0 | 0 | 0 | LOW |

---

### 5. Master Register of Transient Unknown Subjects (Tier 3)
The remaining **1,555 unknown individuals** represent transient visitors with 2 to 9 confirmed detections. Due to document size constraints, their individual microsecond timestamps, bounding boxes, and facial quality scores are archived in full in the accompanying master CSV register: [`30_Day_Master_Personas_Behavioral_Register.csv`](file:///d:/facial/30_Day_Master_Personas_Behavioral_Register.csv).
