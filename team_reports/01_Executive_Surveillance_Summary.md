# RO Water Treatment Plant: 30-Day Executive Surveillance Audit
## Executive Briefing & Facility Vulnerability Report

> [!IMPORTANT]
> **CRITICAL AUDIT FINDING: 100% UNREGISTERED / UNKNOWN SUBJECTS**  
> Zero facial profiles in this 30-day surveillance archive match an enrolled employee whitelist or authorized staff database.  
> **All 1,652 detected personas (`SUBJ-01` through `SUBJ-1652`) are legally and forensically classified as UNKNOWN PERSONS (Pending Identification & Formal Enrollment).**  
> Grouping into Tiers (Tier 1, 2, 3) reflects statistical sighting frequency and recurrence only—**NOT confirmed employment, clearance, or staff authorization.**

> [!NOTE]
> **Target Location:** RO Water Treatment Plant Rooftop Deck | Camera `IPC56`  
> **Coverage Window:** September 1, 2026 – September 30, 2026 (713.66 Continuous Facility Hours)  
> **Target Audience:** Plant Management, Facility Operations, and Executive Leadership  

---

### 1. Executive Overview & Mission Summary
An autonomous forensic and biometric surveillance audit was conducted over 30 continuous calendar days of native 3K CCTV footage covering the RO Water Treatment Plant rooftop. The audit established continuous tracking of all human activity in the mechanical wing, measured shift-by-shift recurrence patterns, resolved historical video clipping blindspots, and logged every direct physical contact event against mission-critical equipment assets.

### 2. Key Operational Metrics

| Metric | Value | Operational Security Context |
| :--- | :--- | :--- |
| **Continuous Coverage** | **713.66 Hours (30 Days)** | 100% of recorded footage across September 2026 evaluated |
| **Total Discovered Personas** | **1,652 Unique Personas** | **100% Unknown / Unregistered Individuals** grouped via ArcFace clustering |
| **High-Frequency Unknown Subjects** | **12 Individuals** | Tier 1 recurring unknown subjects ($\ge 50$ detections each) |
| **Periodic Unknown Subjects** | **85 Individuals** | Tier 2 medium-frequency unknown subjects ($10 - 49$ detections) |
| **Transient / Single-Visit Subjects** | **1555 Individuals** | Tier 3 low-frequency unknown subjects ($2 - 9$ detections) |
| **Direct Equipment Contact Breaches** | **18 Unknown Individuals** | Verified touching high-hazard valves, skid controls, or electrical breaker switch |
| **Pristine Incident Video Clips** | **179 Events (8.20 GB)** | Fully extracted with mandatory $\pm 60$s pre/post contextual safety buffers |
| **Total Processed Face Vectors** | **36,226 Vectors** | High-quality 512-D embeddings ($Q \ge 40$) evaluated |

### 3. Operational Shift Recurrence Patterns
- **Shift A (Morning, 06:00 – 13:59):** **24,597 detections (68.0%)** — Peak operating window where recurring unknown subjects routinely operated valves and visited the skid.
- **Shift B (Afternoon, 14:00 – 21:59):** **11,188 detections (30.9%)** — Secondary activity window with multiple unknown subjects traversing the terrace corridor.
- **Shift C (Night Vigilance, 22:00 – 05:59):** **413 detections (1.1%)** — Nighttime visits, perimeter walkthroughs, and physical contact with the main electrical breaker switch.

### 4. 30-Day Critical & Severe Incident Investigations (Days 01 – 30)
Across the 30 continuous calendar days (713.66 recorded hours), 179 physical equipment interaction events were captured and investigated across all four operational weeks:

1. **Severe Power Breaker Switch Access (Zone 2 — 5 Breaches across 4 Days):**
   - **Day 09 (`16:21:55` & `16:24:51`):** Two consecutive breaches where multiple unknown subjects accessed the main electrical power breaker switch (`EVT-D09-005` involving `SUBJ-233`, `SUBJ-759`, `SUBJ-760` [162s] and `EVT-D09-006` involving `SUBJ-13`, `SUBJ-347` [125s]).
   - **Day 11 (`06:33:37`):** Early morning unauthorized contact with the main breaker switch by `SUBJ-791` (`EVT-D11-001` [121s]).
   - **Day 24 (`16:39:26`):** Physical manipulation of the main power switch by `SUBJ-1079` (`EVT-D24-013` [121s]).
   - **Day 25 (`11:43:10`):** Midday power switch contact by `SUBJ-1088` (`EVT-D25-002` [121s]).

2. **Critical Multiport Backwash Valve Operations (Zone 1A/B — 54 Events across 23 Days):**
   - **Week 1 (Days 01–07, 9 events):** Routine morning backwash operations, including Day 1 events (`SUBJ-01` at `07:29` & `08:14`, and `SUBJ-1652` at `09:53:38`).
   - **Week 2 (Days 08–14, 13 events):** Daily operational cycling by Tier 1 and Tier 2 unknown subjects.
   - **Week 3 (Days 15–21, 17 events):** Peak critical activity window, featuring Day 15 multi-subject group access (5 valve operations involving 10 unknown subjects).
   - **Week 4 (Days 22–26, 15 events):** Frequent high-contact days including Day 25 (4 valve operations) and Day 26 mass gathering (3 events, 34 unknown subjects on deck).

3. **Shift C Night Vigilance Breaches (22:00 – 05:59):**
   - Off-hours deck access detected on Day 01 (`22:27:36`), Day 15 (`23:24:04`), and Day 29 (`23:14:10`) where unknown individuals accessed the equipment deck outside scheduled plant hours.

### 5. Forensic Pipeline Bug Resolutions & Universal 30-Day Fixes
Day 1 served as the initial forensic calibration testbed, uncovering critical software failure modes that prompted universal fixes across all 30 days:
1. **Premature Motion Window Cutoff:** Clip 14 (`094423.mp4`) automated scanner timed out after 42s, missing the `09:53:38` valve manipulation. Resolved by deploying rolling continuous temporal windows and enrolling the operator as `SUBJ-1652` (verified distinct from `SUBJ-02`, cosine sim `0.1831`).
2. **File Split Boundary Truncation:** Clip boundary at `22:28:00` cut off the Day 1 `22:27:36` breaker contact. Resolved by enforcing mandatory $\pm 60$s contextual safety buffers bridging adjacent video files across all 179 incident clips.
3. **Database Timestamp Inversion Bug:** Fixed SQL ordering bug that generated inverted timestamps in 29/30 CSV files; all 30 clipping indices now have **0 inverted timestamps** across all 179 events.

### 6. Immediate Security Recommendations
- **Mandatory Personnel Enrollment:** Conduct an immediate formal identity verification round with facility HR to associate names and employment status with the 1,652 unknown subject clusters (`SUBJ-01` to `SUBJ-1652`).
- **Physical Access Restriction:** Secure Zone 1A/B Multiport Valves and Zone 2 Power Switch with physical lockout/tagout (LOTO) padlock enclosures to prevent unauthorized operation.
- **Automated Contact Alerting:** Deploy the calibrated spatial ROI mesh (`IoU > 0.08`) for real-time audible alarms whenever an unregistered individual approaches within 40px of critical equipment.