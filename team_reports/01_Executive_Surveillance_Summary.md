# Forensic Surveillance Audit: RO Water Treatment Plant
## Executive Briefing & Facility Vulnerability Assessment (30-Day Audit)

### Document Control & Audit Metadata
| Parameter | Specification / Audit Scope |
| :--- | :--- |
| **Monitored Facility** | RO Water Treatment Plant Rooftop Mechanical Deck |
| **Primary Sensor** | Fixed Overhead 3K IP Camera (`IPC56`) |
| **Surveillance Window** | September 1, 2026 00:00:00 – September 30, 2026 23:59:59 |
| **Continuous Coverage** | 713.66 Recorded Facility Hours (999 Raw CCTV Video Segments) |
| **Audit Classification** | Official Forensic Surveillance & Biometric Audit Report |
| **Personnel Status** | 100% Unregistered Personnel (Pending Identity Verification & Formal Enrollment) |

---

### 1. Forensic Identification Statement
Zero facial profiles in this 30-day surveillance archive match an enrolled employee whitelist or authorized plant personnel database. Consequently, all 1,652 identified personas (designated `SUBJ-01` through `SUBJ-1652`) are formally classified as **Unregistered Subjects / Unknown Persons**. Categorization into sighting frequency tiers denotes statistical recurrence volume only and does not establish employment status, job function, or access clearance.

### 2. Verified Operational & Security Metrics

| Metric Category | Verified Audit Metric | Security & Operational Context |
| :--- | :--- | :--- |
| **Continuous Facility Coverage** | **713.66 Recorded Hours** | 30 continuous calendar days (99.12% facility uptime across 999 clips) |
| **Total Discovered Personas** | **1,652 Unique Personas** | 100% Unknown Persons cataloged via unsupervised ArcFace 512-D clustering |
| **High-Frequency Unknowns (Tier 1)** | **12 Individuals** | Recurring unknown subjects with $\ge 50$ detections each |
| **Periodic Unknowns (Tier 2)** | **85 Individuals** | Recurring unknown subjects with $10 - 49$ detections |
| **Transient Unknowns (Tier 3)** | **1,555 Individuals** | Low-frequency unknown subjects with $2 - 9$ detections |
| **Direct Equipment Contact Breaches** | **18 Unknown Individuals** | Verified touching multiport valves, skid controls, or electrical breaker switch |
| **Lossless Incident Video Clips** | **179 Events (8.20 GB)** | Fully extracted with mandatory $\pm 60$s pre/post contextual safety buffers |
| **Total Processed Face Vectors** | **36,226 Vectors** | High-quality 512-D embeddings ($Q \ge 40$) evaluated |

### 3. Operational Shift Recurrence Patterns
- **Shift A (Morning, 06:00 – 13:59):** **24,625 detections (68.0%)** — Primary activity window where recurring unknown subjects routinely operated valves and inspected the RO skid.
- **Shift B (Afternoon, 14:00 – 21:59):** **11,188 detections (30.9%)** — Secondary activity window with multiple unknown subjects traversing the terrace corridor.
- **Shift C (Night Vigilance, 22:00 – 05:59):** **413 detections (1.1%)** — Off-hours access events including perimeter walkthroughs and main electrical breaker switch contacts.

### 4. 30-Day Critical & Severe Incident Investigations (Days 01 – 30)
Across the 30 continuous calendar days, **179 physical equipment interaction events** were verified and cataloged across three equipment hazard tiers:

#### 4.1. Severe Power Breaker Switch Access (Zone 2 — 5 Events across 4 Days)
The plant's main electrical breaker switch was directly accessed in 5 separate incidents by unauthorized unknown subjects:

| Day & Timestamp | Event ID | Critical Asset | Unknown Personas Involved | Duration |
| :--- | :--- | :--- | :--- | :--- |
| Day 09 `16:21:55` | `EVT-D09-005` | Ultimate Plant Power Switch (Zone 2) | SUBJ-233;SUBJ-759;SUBJ-760 | 162s |
| Day 09 `16:24:51` | `EVT-D09-006` | Ultimate Plant Power Switch (Zone 2) | SUBJ-13;SUBJ-347 | 125s |
| Day 11 `06:33:37` | `EVT-D11-001` | Ultimate Plant Power Switch (Zone 2) | SUBJ-791 | 121s |
| Day 24 `16:39:26` | `EVT-D24-013` | Ultimate Plant Power Switch (Zone 2) | SUBJ-1079 | 121s |
| Day 25 `11:43:10` | `EVT-D25-002` | Ultimate Plant Power Switch (Zone 2) | SUBJ-1088 | 121s |

#### 4.2. Critical Multiport Backwash Valve Operations (Zone 1A/B — 54 Events across 23 Days)
Manual multiport backwash valves controlling high-pressure sand, carbon, and membrane filtration were operated repeatedly across the month:
- **Week 1 (Days 01–07, 9 events):** Routine morning backwash operations (Days 1, 2, 6, 7), including Day 1 operations (`SUBJ-01` at `07:29` and `08:14`, and `SUBJ-1652` at `09:53:38`).
- **Week 2 (Days 08–14, 13 events):** Daily operational cycling by Tier 1 and Tier 2 unknown subjects.
- **Week 3 (Days 15–21, 17 events):** Peak critical activity window, featuring Day 15 multi-subject group access (5 valve operations involving 10 unknown subjects).
- **Week 4 (Days 22–26, 15 events):** High-frequency valve operations including Day 25 (4 valve operations) and Day 26 mass gathering (3 events, 34 unknown subjects on deck).

#### 4.3. Off-Hours Night Vigilance Breaches (Shift C, 22:00 – 05:59)
Off-hours deck access was documented on Day 01 (`22:27:36`), Day 15 (`23:24:04`), and Day 29 (`23:14:10`), where unknown individuals accessed the equipment deck outside scheduled plant operating hours.

### 5. Evidence Continuity & Forensic Quality Assurance
1. **Rolling Continuous Temporal Windows:** Replaced static segment cutoffs with rolling temporal windowing, eliminating blindspots across continuous 45-minute CCTV segments.
2. **Contextual Safety Buffers ($\pm 60$s):** All 179 extracted incidents feature mandatory 60-second pre- and post-event safety margins that bridge video file splits without loss of visual context.
3. **Biometric Separation & Enrollment (`SUBJ-1652`):** Verified the Day 1 `09:53:38` valve operator is distinct from `SUBJ-02` (ArcFace cosine similarity `0.1831`, far below the $\ge 0.4500$ threshold). Formally enrolled the subject as `SUBJ-1652`.
4. **Chronological ISO 8601 Wall-Clock Ordering:** Rebuilt all 30 clipping indices with strict chronological sorting, achieving 0 timestamp inversions across all 179 events.

### 6. Facility Security & Compliance Recommendations
1. **Mandatory Personnel Enrollment:** Execute a formal identification drive with facility administration to associate legal identities with all 1,652 unknown persona clusters (`SUBJ-01` to `SUBJ-1652`).
2. **Physical Access Restriction:** Install Lockout/Tagout (LOTO) padlock enclosures on Zone 1A/B Multiport Valves and the Zone 2 Main Power Breaker Switch to prevent unrecorded manual operation.
3. **Automated Spatial Gating Alarms:** Deploy the calibrated spatial ROI mesh (`IoU > 0.08`) for real-time audible alarms whenever an unregistered individual approaches within 40px of critical equipment.
