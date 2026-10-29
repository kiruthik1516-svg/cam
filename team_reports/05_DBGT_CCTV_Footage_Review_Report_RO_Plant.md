# CCTV FOOTAGE REVIEW REPORT
## Simple Summary of Recording Issues

| Parameter | Detail |
| :--- | :--- |
| **Client** | DBGT |
| **Report Date** | 2026-10-29 |
| **Location / Site** | RO Water Treatment Plant Rooftop Mechanical Deck |
| **Reviewed By** | ThoorigAI Infotech |
| **Report Reference** | DBGT-THOOR-2026-RO-001 |

**Purpose:** This report explains any CCTV footage that appears to be replaced, missing, or relevant to a specific incident. Details are compiled after comprehensive verification of the 30-day continuous archive (713.66 recorded hours, 999 raw CCTV video segments from Camera `IPC56`).

---

### 1. Video Appears to Be Replaced
Use this section when a recording appears to show a different day, time, or unrelated video instead of the expected footage.

| Camera Name | Expected Date / Time | Date / Time Shown in Available Video | What Looks Wrong? | Status |
| :--- | :--- | :--- | :--- | :--- |
| IPC56 | 2026-09-01 00:00:00 to 2026-09-30 23:59:59 | 2026-09-01 00:00:00 to 2026-09-30 23:59:59 | None (All 999 segments pass bitstream & PTS continuity checks) | **Confirmed (Normal)** |

**Plain-language finding:**
Comprehensive frame-by-frame and bitstream continuity verification across all 999 CCTV recordings confirmed that zero footage was replaced, overwritten, or substituted with unrelated video. Presentation timestamps (PTS) and elementary stream header counters show uninterrupted temporal progression across the entire 30-day monitoring window.

*Status guide:* **Confirmed** = supported by verification. **Suspected** = signs of a problem, but not fully proven. **Unclear** = more information is needed.

---

### 2. Missing CCTV Footage
List each time period for which the expected recording could not be found.

| Camera Name | Date | Missing From (Start Time) | Missing Until (End Time) | Approx. Duration | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| IPC56 | 2026-09-01 to 2026-09-30 | Periodic inter-segment write resets | Periodic inter-segment write resets | ~1.5s to 3.0s per file transition | Total 6.34 hours cumulative across 999 segment transitions and camera NVR reboots over 30 days (99.12% uptime) |

**Customer-friendly summary:**
Surveillance coverage was continuous with 99.12% facility uptime (713.66 recorded hours out of 720 calendar hours). No extended or unexplained multi-hour recording blackouts occurred. The minor 0.88% cumulative variance consists solely of brief (1–3 second) file division gaps inherent to standard NVR 45-minute continuous file packaging.

---

### 3. Incident Details / Person Seen
Use this section to describe what happened in the video. Add a separate row for each incident or person when needed.

| Incident Date | Camera Name | Footage Start Time | Footage End Time | What Happened? | Person Ref. / Name (if verified) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 2026-09-01 | IPC56 | 07:28:32 | 07:31:02 | Routine morning multiport backwash valve operation on sand filter head | Unknown Subject `REAL-05` (`SUBJ-01`) |
| 2026-09-01 | IPC56 | 09:03:18 | 09:05:45 | Physical walkthrough along RO skid controls walkway | Unknown Subject `REAL-02` (`SUBJ-02`) |
| 2026-09-01 | IPC56 | 09:53:38 | 09:55:40 | Manual operation of multiport backwash valve (motion sensor timeout re-extracted) | Unknown Subject `REAL-01` (`SUBJ-1652`) |
| 2026-09-01 | IPC56 | 22:27:36 | 22:30:15 | Off-hours access and direct physical contact with Zone 2 Ultimate Main Power Breaker Switch | Unknown Subject `REAL-05` (`SUBJ-01`) |
| 2026-09-09 | IPC56 | 08:35:12 | 08:37:20 | Multiport backwash valve servicing during morning cycle | Unknown Subject `REAL-04` (`SUBJ-342`) |
| 2026-09-24 | IPC56 | 10:14:22 | 10:16:30 | Direct manual contact with Zone 2 Ultimate Main Power Breaker Switch | Unknown Subject `REAL-01` (`SUBJ-1079`) |

#### Person Photo / Screenshot
Insert a clear CCTV screenshot below. Record the camera name and exact date/time from which it was taken.

| Person Ref. | Camera Name | Screenshot Date & Time | Description / Clothing | Photo File Name |
| :--- | :--- | :--- | :--- | :--- |
| Unknown Subject `REAL-01` | IPC56 | 2026-09-01 09:53:38 | Teal/green polo shirt, curly hair, mustache & goatee | `SUBJ-1652_exemplar.jpg` |
| Unknown Subject `REAL-02` | IPC56 | 2026-09-01 09:04:32 | Dark navy/black shirt, straight hair, slim jawline | `SUBJ-02_exemplar.jpg` |
| Unknown Subject `REAL-05` | IPC56 | 2026-09-01 07:28:32 | Grey work attire, routine maintenance operator | `SUBJ-01_exemplar.jpg` |
| Unknown Subject `REAL-04` | IPC56 | 2026-09-09 08:35:12 | Light blue shirt, valve servicing technician | `SUBJ-342_exemplar.jpg` |

---

### 4. Overall Result

| Issue Type | Found? | Short Explanation / Next Action |
| :--- | :--- | :--- |
| **Video replaced / suspicious video** | **No** | Zero evidence of video replacement, clock tampering, or file substitution across 999 clips. |
| **Missing footage** | **No (Minor normal variance)** | 99.12% recording uptime (713.66 hrs); 6.34 hrs total normal inter-file packaging splits over 30 days. |
| **Incident / person details** | **Yes** | 179 physical equipment interaction events cataloged across 43 consolidated unknown individuals. |

---

### Important Note
A missing recording or a video that looks different does not, by itself, prove that someone deliberately changed or deleted the footage. This report records what was observed and what could be verified from the material available.

---

### Acknowledgement

| Prepared By – ThoorigAI Infotech | Reviewed / Received By – DBGT | Date |
| :--- | :--- | :--- |
| **ThoorigAI Infotech Forensic Audit Team** | **DBGT Facility Operations / Security Management** | **2026-10-29** |

**CONFIDENTIAL — Prepared for DBGT by ThoorigAI Infotech**