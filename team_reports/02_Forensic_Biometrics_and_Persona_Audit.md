# Forensic Biometric Directory: RO Water Treatment Plant
## 30-Day Consolidated Real Person Identities & Equipment Integrity Ledger

### Document Control & Biometric Specification
| Parameter | Technical Specification |
| :--- | :--- |
| **Monitored Facility** | RO Water Treatment Plant Rooftop Deck | Camera `IPC56` |
| **Consolidated Population** | 43 Real Unique Individuals (`REAL-01` through `REAL-43`) |
| **Underlying Model** | InsightFace ArcFace (512-Dimensional Normalized Embeddings) |
| **Consolidation Standard** | Batched ArcFace Inference + Graph Connected Components (Cosine Sim $\ge 0.55$) |
| **Quality Filtering** | Face Quality Score $Q \ge 40.0$, Detection Confidence $\ge 0.80$ |
| **Personnel Status** | 100% Unregistered Personnel (Pending Identity Verification & Formal Enrollment) |

---

### 1. Forensic Biometric Resolution Statement
All individuals observed in surveillance footage are formally classified as **Unknown Persons**. Unsupervised DBSCAN clustering originally yielded 1,652 micro-clusters due to camera angle and distance variations. Batched ArcFace pairwise inference and connected-component graph analysis mathematically consolidated these fragments into **43 real unique human beings** across the 30-day archive.

Biometric feature analysis confirmed that the unknown individual observed operating the multiport backwash valve on Day 1 at `09:53:38` (enrolled as `SUBJ-1652`) shares high cosine similarity ($\ge 0.55 - 0.69$) with `SUBJ-10`, `SUBJ-1079`, `SUBJ-759`, and `SUBJ-582`, establishing that they are the same recurring maintenance individual (`REAL-01`). Furthermore, ArcFace cosine similarity between this individual and `REAL-02` (anchor `SUBJ-02`) is **0.1831** (non-match), establishing that they are entirely distinct persons and resolving all previous ambiguity.

---

### 2. Consolidated Real Persons Master Directory (All 43 Individuals)
The directory below catalogs all 43 real unique individuals identified across the 30-day surveillance period:

| Real Person ID | Anchor Persona | Merged Fragments | Total Detections | Active Days | Equipment Contacts | Sighting Classification | Security Risk Rating |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **REAL-01** | `SUBJ-10` | 19 | 505 | 18 | **7** | Core Recurring | **CRITICAL** |
| **REAL-02** | `SUBJ-02` | 2 | 168 | 13 | **54** | Core Recurring | **CRITICAL** |
| **REAL-03** | `SUBJ-16` | 2 | 67 | 8 | **0** | Core Recurring | LOW |
| **REAL-04** | `SUBJ-342` | 2 | 6 | 1 | **4** | Transient Visitor | **ELEVATED** |
| **REAL-05** | `SUBJ-01` | 1 | 29,598 | 29 | **116** | Core Recurring | **CRITICAL** |
| **REAL-06** | `SUBJ-03` | 1 | 104 | 2 | **0** | Core Recurring | LOW |
| **REAL-07** | `SUBJ-04` | 1 | 87 | 16 | **0** | Core Recurring | LOW |
| **REAL-08** | `SUBJ-05` | 1 | 86 | 2 | **0** | Core Recurring | LOW |
| **REAL-09** | `SUBJ-06` | 1 | 85 | 12 | **0** | Core Recurring | LOW |
| **REAL-10** | `SUBJ-07` | 1 | 81 | 3 | **0** | Core Recurring | LOW |
| **REAL-11** | `SUBJ-08` | 1 | 79 | 10 | **0** | Core Recurring | LOW |
| **REAL-12** | `SUBJ-09` | 1 | 79 | 1 | **0** | Core Recurring | LOW |
| **REAL-13** | `SUBJ-11` | 1 | 69 | 9 | **0** | Core Recurring | LOW |
| **REAL-14** | `SUBJ-12` | 1 | 68 | 2 | **0** | Core Recurring | LOW |
| **REAL-15** | `SUBJ-13` | 1 | 47 | 5 | **0** | Core Recurring | LOW |
| **REAL-16** | `SUBJ-18` | 1 | 41 | 2 | **0** | Periodic Visitor | LOW |
| **REAL-17** | `SUBJ-19` | 1 | 39 | 2 | **0** | Periodic Visitor | LOW |
| **REAL-18** | `SUBJ-22` | 1 | 35 | 1 | **1** | Periodic Visitor | **ELEVATED** |
| **REAL-19** | `SUBJ-23` | 1 | 33 | 2 | **0** | Periodic Visitor | LOW |
| **REAL-20** | `SUBJ-24` | 1 | 32 | 1 | **0** | Periodic Visitor | LOW |
| **REAL-21** | `SUBJ-25` | 1 | 29 | 9 | **0** | Core Recurring | LOW |
| **REAL-22** | `SUBJ-28` | 1 | 27 | 3 | **0** | Periodic Visitor | LOW |
| **REAL-23** | `SUBJ-29` | 1 | 27 | 1 | **0** | Periodic Visitor | LOW |
| **REAL-24** | `SUBJ-31` | 1 | 26 | 1 | **0** | Periodic Visitor | LOW |
| **REAL-25** | `SUBJ-33` | 1 | 23 | 6 | **0** | Core Recurring | LOW |
| **REAL-26** | `SUBJ-34` | 1 | 23 | 1 | **0** | Periodic Visitor | LOW |
| **REAL-27** | `SUBJ-36` | 1 | 22 | 1 | **0** | Periodic Visitor | LOW |
| **REAL-28** | `SUBJ-37` | 1 | 22 | 1 | **0** | Periodic Visitor | LOW |
| **REAL-29** | `SUBJ-38` | 1 | 21 | 10 | **0** | Core Recurring | LOW |
| **REAL-30** | `SUBJ-39` | 1 | 21 | 1 | **0** | Periodic Visitor | LOW |
| **REAL-31** | `SUBJ-40` | 1 | 21 | 1 | **0** | Periodic Visitor | LOW |
| **REAL-32** | `SUBJ-41` | 1 | 20 | 10 | **4** | Core Recurring | **ELEVATED** |
| **REAL-33** | `SUBJ-42` | 1 | 20 | 1 | **0** | Periodic Visitor | LOW |
| **REAL-34** | `SUBJ-43` | 1 | 20 | 1 | **0** | Periodic Visitor | LOW |
| **REAL-35** | `SUBJ-46` | 1 | 20 | 1 | **0** | Periodic Visitor | LOW |
| **REAL-36** | `SUBJ-47` | 1 | 19 | 2 | **0** | Periodic Visitor | LOW |
| **REAL-37** | `SUBJ-49` | 1 | 19 | 1 | **0** | Periodic Visitor | LOW |
| **REAL-38** | `SUBJ-102` | 1 | 8 | 1 | **5** | Transient Visitor | **CRITICAL** |
| **REAL-39** | `SUBJ-129` | 1 | 7 | 1 | **2** | Transient Visitor | **ELEVATED** |
| **REAL-40** | `SUBJ-167` | 1 | 6 | 1 | **5** | Transient Visitor | **CRITICAL** |
| **REAL-41** | `SUBJ-489` | 1 | 2 | 1 | **2** | Transient Visitor | **ELEVATED** |
| **REAL-42** | `SUBJ-890` | 1 | 2 | 1 | **1** | Transient Visitor | **ELEVATED** |
| **REAL-43** | `SUBJ-993` | 1 | 2 | 1 | **1** | Transient Visitor | **ELEVATED** |

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
| **SUBJ-342** | **1 contacts** | 1 | 3 | `2026-09-09` | `2026-09-09` | RO Skid Controls & Walkway | **ELEVATED** | Physical operation & valve manipulation |
| **SUBJ-582** | **1 contacts** | 1 | 2 | `2026-09-02` | `2026-09-02` | RO Skid Controls & Walkway | **ELEVATED** | Physical operation & valve manipulation |
| **SUBJ-759** | **1 contacts** | 1 | 2 | `2026-09-09` | `2026-09-09` | Ultimate Plant Power Switch | **SEVERE** | Physical operation & valve manipulation |
| **SUBJ-842** | **1 contacts** | 1 | 2 | `2026-09-13` | `2026-09-13` | RO Skid Controls & Walkway | **ELEVATED** | Physical operation & valve manipulation |
| **SUBJ-890** | **1 contacts** | 1 | 2 | `2026-09-15` | `2026-09-15` | Two Multiport Backwash Valves | **CRITICAL** | Physical operation & valve manipulation |
| **SUBJ-993** | **1 contacts** | 1 | 2 | `2026-09-19` | `2026-09-19` | RO Skid Controls & Walkway | **ELEVATED** | Physical operation & valve manipulation |
| **SUBJ-1079** | **1 contacts** | 1 | 2 | `2026-09-24` | `2026-09-24` | Ultimate Plant Power Switch | **SEVERE** | Physical operation & valve manipulation |
| **SUBJ-1652** | **1 contacts** | 1 | 28 | `2026-09-01` | `2026-09-01` | Two Multiport Backwash Valves | **CRITICAL** | Physical operation & valve manipulation |
