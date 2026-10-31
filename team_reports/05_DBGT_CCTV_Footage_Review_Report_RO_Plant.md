<p align="right"><img src="thoorigai_logo.jpg" alt="ThoorigAI Infotech Logo" width="65" /></p>

# CCTV FOOTAGE REVIEW REPORT
## Simple Summary of Recording Issues

| Parameter | Detail |
| :--- | :--- |
| **Client** | DBGT |
| **Report Date** | 2026-10-29 |
| **Location / Site** | RO Water Treatment Plant Rooftop Mechanical Deck |
| **Reviewed By** | ThoorigAI Infotech |
| **Report Reference** | DBGT-THOOR-2026-RO-001 |

**Purpose:** This report explains any CCTV footage that appears to be replaced, missing, or relevant to a specific incident. Details are compiled after comprehensive forensic verification of the physical 30-day continuous archive (719.65 recorded hours from Camera `IPC56`, 99.95% coverage across 998 physical files).

---

### 1. Video Appears to Be Replaced
Use this section when a recording appears to show a different day, time, or unrelated video instead of the expected footage.

| Camera Name | Expected Date / Time | Date / Time Shown in Available Video | What Looks Wrong? | Status |
| :--- | :--- | :--- | :--- | :--- |
| IPC56 | 2026-09-27 00:00:00 to 2026-09-27 23:59:59 (Day 27) | 2026-09-26 00:00:00 to 2026-09-26 23:59:59 (Day 26) | All 33 clips in Day 27 are identical bit-for-bit file duplicates of Day 26 (matching 5,444 crops, 90.6m activity duration). Actual Sept 27 footage was substituted. | **Confirmed (Replaced / Duplicated)** |

**Plain-language finding:**
Temporal bitstream, file hash, and candidate crop analysis confirmed that all 33 video segments archived under Day 27 (`2026-09-27`) are identical duplicate copies of Day 26 (`2026-09-26`). Both directories record exactly 5,444 candidate face crops and 90.6 minutes of active movement with matching presentation timestamps. This confirms that legitimate CCTV footage for Sunday, September 27 was replaced with re-dated Day 26 recordings.

*Status guide:* **Confirmed** = supported by verification. **Suspected** = signs of a problem, but not fully proven. **Unclear** = more information is needed.

---

### 2. Missing CCTV Footage
List each time period for which the expected recording could not be found.

| Camera Name | Date | Missing From (Start Time) | Missing Until (End Time) | Approx. Duration | Root Cause / Operational Pattern |
| :--- | :--- | :--- | :--- | :--- | :--- |
| IPC56 | 2026-09-07 (Day 07, Mon) | 09:40:14 | 09:42:40 | 2.4 mins | Automated Weekly NVR Reboot (09:40 AM) |
| IPC56 | 2026-09-08 (Day 08, Tue) | 14:45:37 | 15:04:23 | 18.8 mins | Inter-Clip Buffer Hitch / Plant Electrical Maintenance |
| IPC56 | 2026-09-14 (Day 14, Mon) | 09:40:14 | 09:42:42 | 2.4 mins | Automated Weekly NVR Reboot (09:40 AM) |
| IPC56 | 2026-09-20 (Day 20, Sun) | 23:42:00 | 23:43:22 | 1.4 mins | Inter-Clip Buffer Hitch |
| IPC56 | 2026-09-21 (Day 21, Mon) | 09:40:14 | 09:42:39 | 2.4 mins | Automated Weekly NVR Reboot (09:40 AM) |
| IPC56 | 2026-09-28 (Day 28, Mon) | 09:40:16 | 09:42:41 | 2.4 mins | Automated Weekly NVR Reboot (09:40 AM) |

**Customer-friendly summary:**
Surveillance coverage achieved **719.65 recorded hours** across the 30-day month (**99.95% timeline coverage** across all 998 physical MP4 files). Comprehensive ground-truth verification directly against the physical master storage media confirmed that the CCTV recording maintained near-continuous uptime. Across the entire 720-hour month, **only 6 verified recording gaps occurred, totaling 29.8 minutes (0.50 hours)**:
1. **Automated Weekly Maintenance Reboot (4 events):** Every Monday morning at exactly 09:40 AM (Days 07, 14, 21, 28), the NVR performed a scheduled 2.4-minute maintenance reboot.
2. **Inter-Clip Buffer Hitches & Plant Maintenance (2 events):** Tuesday afternoon on Day 08 experienced an 18.8-minute recording interruption (14:45:37–15:04:23), and Sunday late night on Day 20 experienced a brief 1.4-minute buffer hitch (23:42:00–23:43:22).
*Verification Note on Day 21 Morning Block:* Forensic physical disk inspection confirmed that the previously suspected 44.9-minute morning block on Day 21 (07:17:44–08:02:40) is 100% intact and present on disk (`56_8_DBGT_IPC56_df605109..._20260921071744.mp4`, 1.06 GB, 80,920 frames). The entire 30-day archive contains zero dropped 45-minute recording blocks.

---

### 3. Incident Details / Person Seen
Use this section to describe what happened in the video. All 20 manually verified and confirmed equipment interaction incidents:

> **Universal Alert Standard:** *Alert triggered due to physical presence / activity detected in monitored equipment area.*<br/>
> *Note on Event Descriptions:* Because specific component-level interaction or operational motive cannot be determined from video footage alone, all events are recorded with the standardized universal alert description above.

> **Attached Google Drive Folder (All 20 Confirmed Incident Video Clips):**<br/>
> **[https://drive.google.com/drive/folders/1uhX9iv6-uBRRgBP4xMopMYQNWnKL6oYo](https://drive.google.com/drive/folders/1uhX9iv6-uBRRgBP4xMopMYQNWnKL6oYo)**<br/>
> *(All 20 lossless MP4 video clips with $\pm 60$s contextual margins are accessible in this single shared drive folder)*

| Incident Date | Camera Name | Footage Start Time | Footage End Time | What Happened? | Person Ref. / Name (if verified) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 2026-09-01 | IPC56 | 09:52:38 | 09:54:38 | Alert triggered due to physical presence / activity detected in monitored equipment area | Unknown Subject `REAL-01 (SUBJ-1652)` |
| 2026-09-01 | IPC56 | 22:26:36 | 22:28:35 | Alert triggered due to physical presence / activity detected in monitored equipment area | Unknown Subject `REAL-05 (SUBJ-01)` |
| 2026-09-07 | IPC56 | 07:38:27 | 07:40:27 | Alert triggered due to physical presence / activity detected in monitored equipment area | Unknown Subject `REAL-07` |
| 2026-09-09 | IPC56 | 01:50:18 | 01:52:19 | Alert triggered due to physical presence / activity detected in monitored equipment area | Unknown Subject `REAL-06` |
| 2026-09-09 | IPC56 | 10:39:19 | 10:41:20 | Alert triggered due to physical presence / activity detected in monitored equipment area | Unknown Subject `REAL-01 (SUBJ-10)` |
| 2026-09-09 | IPC56 | 22:01:06 | 22:03:06 | Alert triggered due to physical presence / activity detected in monitored equipment area | Unknown Subject `REAL-01 (SUBJ-10)` |
| 2026-09-11 | IPC56 | 06:32:37 | 06:34:39 | Alert triggered due to physical presence / activity detected in monitored equipment area | Unknown Subject `REAL-29` |
| 2026-09-11 | IPC56 | 09:49:20 | 09:51:11 | Alert triggered due to physical presence / activity detected in monitored equipment area | Unknown Subject `REAL-23` |
| 2026-09-11 | IPC56 | 14:15:46 | 14:18:05 | Alert triggered due to physical presence / activity detected in monitored equipment area | Unknown Subject `REAL-22` |
| 2026-09-11 | IPC56 | 14:40:33 | 14:42:41 | Alert triggered due to physical presence / activity detected in monitored equipment area | Unknown Subject `REAL-24` |
| 2026-09-11 | IPC56 | 15:30:52 | 15:32:54 | Alert triggered due to physical presence / activity detected in monitored equipment area | Unknown Subject `REAL-04 (SUBJ-342)` |
| 2026-09-15 | IPC56 | 10:33:08 | 10:35:09 | Alert triggered due to physical presence / activity detected in monitored equipment area | Unknown Subject `REAL-03` |
| 2026-09-24 | IPC56 | 08:10:51 | 08:12:52 | Alert triggered due to physical presence / activity detected in monitored equipment area | Unknown Subject `REAL-01` |
| 2026-09-24 | IPC56 | 09:26:39 | 09:28:58 | Alert triggered due to physical presence / activity detected in monitored equipment area | Unknown Subject `REAL-01` |
| 2026-09-24 | IPC56 | 16:14:33 | 16:15:01 | Alert triggered due to physical presence / activity detected in monitored equipment area | Unknown Subject `REAL-01` |
| 2026-09-24 | IPC56 | 16:38:26 | 16:40:28 | Alert triggered due to physical presence / activity detected in monitored equipment area | Unknown Subject `REAL-01 (SUBJ-1079)` |
| 2026-09-25 | IPC56 | 11:42:10 | 11:43:44 | Alert triggered due to physical presence / activity detected in monitored equipment area | Unknown Subject `REAL-33` |
| 2026-09-25 | IPC56 | 11:44:16 | 11:46:17 | Alert triggered due to physical presence / activity detected in monitored equipment area | Unknown Subject `REAL-01` |
| 2026-09-26 | IPC56 | 07:44:59 | 07:48:54 | Alert triggered due to physical presence / activity detected in monitored equipment area | Unknown Subject `REAL-05` |
| 2026-09-26 | IPC56 | 07:49:09 | 07:51:23 | Alert triggered due to physical presence / activity detected in monitored equipment area | Unknown Subject `REAL-07` |

---

#### Person Photo / Screenshot Record
Insert a clear CCTV screenshot below for all individuals involved in the confirmed equipment interaction incidents above. Record the camera name and exact date/time from which it was taken.

| Photo Crop | Person Ref. | Camera Name | Screenshot Date & Time | Description / Clothing | Incidents Linked | Identification Status |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- |
| <img src="person_crops/REAL-01_verified_face.jpg" alt="REAL-01" width="55" height="60" /> | Unknown Subject **`REAL-01`**<br/>*(Anchor: `SUBJ-10 / SUBJ-1652`)* | IPC56 | 2026-09-01 09:53:38 | Teal/green polo shirt, curly hair, mustache & goatee. Primary recurring operator. | 8 Incidents (EVT-D01-005, EVT-D09-005, EVT-D09-011, EVT-D24-002, EVT-D24-004, EVT-D24-011, EVT-D24-013, EVT-D25-003) | Unregistered Subject (Pending DBGT Enrollment) |
| <img src="person_crops/REAL-03_verified_face.jpg" alt="REAL-03" width="55" height="60" /> | Unknown Subject **`REAL-03`**<br/>*(Anchor: `SUBJ-16`)* | IPC56 | 2026-09-15 10:33:08 | Light coloured work shirt, dark trousers. Morning shift technician. | 1 Incident (EVT-D15-002) | Unregistered Subject (Pending DBGT Enrollment) |
| <img src="person_crops/REAL-04_verified_face.jpg" alt="REAL-04" width="55" height="60" /> | Unknown Subject **`REAL-04`**<br/>*(Anchor: `SUBJ-342`)* | IPC56 | 2026-09-11 15:30:52 | Light blue work shirt. Maintenance technician. | 1 Incident (EVT-D11-006) | Unregistered Subject (Pending DBGT Enrollment) |
| <img src="person_crops/REAL-05_verified_face.jpg" alt="REAL-05" width="55" height="60" /> | Unknown Subject **`REAL-05`**<br/>*(Anchor: `SUBJ-01`)* | IPC56 | 2026-09-01 22:26:36 | Grey work attire, dark hair. Routine maintenance operator. | 2 Incidents (EVT-D01-010, EVT-D26-002) | Unregistered Subject (Pending DBGT Enrollment) |
| <img src="person_crops/REAL-06_verified_face.jpg" alt="REAL-06" width="55" height="60" /> | Unknown Subject **`REAL-06`**<br/>*(Anchor: `SUBJ-03`)* | IPC56 | 2026-09-09 01:50:18 | Dark night vigilance attire, short hair. | 1 Incident (EVT-D09-001) | Unregistered Subject (Pending DBGT Enrollment) |
| <img src="person_crops/REAL-07_verified_face.jpg" alt="REAL-07" width="55" height="60" /> | Unknown Subject **`REAL-07`**<br/>*(Anchor: `SUBJ-04`)* | IPC56 | 2026-09-07 07:38:27 | Dark casual shirt, slim build. Morning servicing operator. | 2 Incidents (EVT-D07-001, EVT-D26-003) | Unregistered Subject (Pending DBGT Enrollment) |
| <img src="person_crops/REAL-22_verified_face.jpg" alt="REAL-22" width="55" height="60" /> | Unknown Subject **`REAL-22`**<br/>*(Anchor: `SUBJ-28`)* | IPC56 | 2026-09-11 14:15:46 | Casual work shirt. Afternoon technician. | 1 Incident (EVT-D11-004) | Unregistered Subject (Pending DBGT Enrollment) |
| <img src="person_crops/REAL-23_verified_face.jpg" alt="REAL-23" width="55" height="60" /> | Unknown Subject **`REAL-23`**<br/>*(Anchor: `SUBJ-29`)* | IPC56 | 2026-09-11 09:49:20 | Blue work attire, short dark hair. Morning technician. | 1 Incident (EVT-D11-003) | Unregistered Subject (Pending DBGT Enrollment) |
| <img src="person_crops/REAL-24_verified_face.jpg" alt="REAL-24" width="55" height="60" /> | Unknown Subject **`REAL-24`**<br/>*(Anchor: `SUBJ-31`)* | IPC56 | 2026-09-11 14:40:33 | Collared shirt, straight dark hair. Maintenance technician. | 1 Incident (EVT-D11-005) | Unregistered Subject (Pending DBGT Enrollment) |
| <img src="person_crops/REAL-29_verified_face.jpg" alt="REAL-29" width="55" height="60" /> | Unknown Subject **`REAL-29`**<br/>*(Anchor: `SUBJ-38`)* | IPC56 | 2026-09-11 06:32:37 | Dark shirt, medium build. Early morning operator. | 1 Incident (EVT-D11-001) | Unregistered Subject (Pending DBGT Enrollment) |
| <img src="person_crops/REAL-33_verified_face.jpg" alt="REAL-33" width="55" height="60" /> | Unknown Subject **`REAL-33`**<br/>*(Anchor: `SUBJ-42`)* | IPC56 | 2026-09-25 11:42:10 | Dark blue work attire. Midday operator. | 1 Incident (EVT-D25-002) | Unregistered Subject (Pending DBGT Enrollment) |

---

### 4. Overall Result

| Issue Type | Found? | Detailed Audit Summary & Next Action |
| :--- | :--- | :--- |
| **Video replaced / suspicious video** | **YES (Confirmed)** | **Sunday Video Substitution Confirmed:** All 33 clips archived under Day 27 (`2026-09-27`) are identical bit-for-bit file duplicates of Day 26 (`2026-09-26`), matching 5,444 candidate crops and 90.6 minutes of activity. Legitimate Sunday footage was substituted with re-dated Day 26 recordings.<br/>*Next Action:* Request original physical NVR backup tapes/drive for Sept 27 to determine whether original footage was overwritten or misfiled. |
| **Missing footage** | **YES (Verified)** | **99.83% Timeline Coverage Maintained:** Total 7 verified recording interruptions totaling 1.25 hours (74.7 minutes) across the 720-hour month. Characterized by scheduled weekly 2.4-min NVR maintenance reboots every Monday at 09:40 AM (Days 07, 14, 21, 28), two buffer hitches (18.8m on Day 08, 1.4m on Day 20), and one 44.9-min morning gap on Day 21 (07:17–08:02). All other standard 45-minute recording segments are fully present.<br/>*Next Action:* Reconfigure Monday 09:40 AM automated reboot schedule to non-operational hours (e.g., Sunday 02:00 AM) and verify network buffer storage. |
| **Incident / person details (20 Confirmed Events)** | **YES (Verified)** | **20 Monitored Equipment Area Alert Events Confirmed:** Across 718.75 monitored hours, exactly 20 physical activity alert events were manually verified and confirmed in the monitored plant equipment deck. Due to camera angle and distance, specific component-level interaction is not definitively determined from footage alone; all 20 events represent verified physical presence and activity in the equipment deck during active surveillance periods.<br/>• **11 Unique Unregistered Personnel:** Exactly 11 individuals were photographed and visually indexed (shown in photo record above). Zero matched an enrolled employee whitelist; 100% are currently classified as Unregistered Personnel pending formal ID verification. Primary operator `REAL-01` was involved in 8 events.<br/>• **Attached Evidence:** All 20 incident clips are accessible in the single shared Google Drive folder: <a href="https://drive.google.com/drive/folders/1uhX9iv6-uBRRgBP4xMopMYQNWnKL6oYo">https://drive.google.com/drive/folders/1uhX9iv6-uBRRgBP4xMopMYQNWnKL6oYo</a><br/>• **Actionable Next Steps:**<br/>1. Conduct formal identity verification with plant administration for the 11 identified individuals.<br/>2. Cross-reference plant operational logbooks against the recorded incident timestamps to verify if these activities corresponded to scheduled maintenance.<br/>3. Review the attached Google Drive incident clips for complete video evidence. |

---

### Important Note
A missing recording or a video that looks different does not, by itself, prove that someone deliberately changed or deleted the footage. This report records what was observed and what could be verified from the material available.

---

### Acknowledgement

| Prepared By – ThoorigAI Infotech | Reviewed / Received By – DBGT | Date |
| :--- | :--- | :--- |
| **ThoorigAI Infotech Forensic Audit Team**<br/>Surveillance Intelligence & Biometrics Division | **DBGT Facility Operations / Security Management**<br/>Facility Asset Custody Administration | **2026-10-29** |

**CONFIDENTIAL — Prepared for DBGT by ThoorigAI Infotech**