#!/usr/bin/env python3
"""
generate_dbgt_review_report.py
Generates the DBGT CCTV Footage Review Report (Simple Summary of Recording Issues)
in both Markdown and executive-grade PDF format.
Prepared for DBGT by ThoorigAI Infotech.
"""

import shutil
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable, Image as RLImage
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

SINGLE_DRIVE_LINK = "https://drive.google.com/drive/folders/1uhX9iv6-uBRRgBP4xMopMYQNWnKL6oYo"
UNIVERSAL_ALERT = "Alert triggered due to physical presence / activity detected in monitored equipment area"

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_decorations(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)
        print(f"[PDF INFO] Total pages generated: {num_pages}")

    def draw_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#64748b"))

        # Header on page 2+
        if self._pageNumber > 1:
            self.drawString(36, 812, "CCTV FOOTAGE REVIEW REPORT // DBGT — THOORIGAI INFOTECH")
            self.drawRightString(559, 812, "CAMERA IPC56 AUDIT")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(36, 806, 559, 806)

        # Footer
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(36, 38, 559, 38)

        self.setFont("Helvetica", 8)
        self.drawString(36, 26, "CONFIDENTIAL — Prepared for DBGT by ThoorigAI Infotech")
        self.drawRightString(559, 26, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()

# Master data of all 20 confirmed incidents with universal alert description
INCIDENTS = [
    {
        "date": "2026-09-01", "cam": "IPC56", "start": "09:52:38", "end": "09:54:38",
        "happened": UNIVERSAL_ALERT,
        "person": "REAL-01 (SUBJ-1652)", "event_id": "EVT-D01-005", "clip": "Day01_EVT-D01-005_CRITICAL_Two_Multiport_Backwash_Valves_20260901_095238.mp4",
    },
    {
        "date": "2026-09-01", "cam": "IPC56", "start": "22:26:36", "end": "22:28:35",
        "happened": UNIVERSAL_ALERT,
        "person": "REAL-05 (SUBJ-01)", "event_id": "EVT-D01-010", "clip": "Day01_EVT-D01-010_SEVERE_Ultimate_Plant_Power_Switch_20260901_222636.mp4",
    },
    {
        "date": "2026-09-07", "cam": "IPC56", "start": "07:38:27", "end": "07:40:27",
        "happened": UNIVERSAL_ALERT,
        "person": "REAL-07", "event_id": "EVT-D07-001", "clip": "Day07_EVT-D07-001_ELEVATED_RO_Skid_Controls_Walkway_20260907_073827.mp4",
    },
    {
        "date": "2026-09-09", "cam": "IPC56", "start": "01:50:18", "end": "01:52:19",
        "happened": UNIVERSAL_ALERT,
        "person": "REAL-06", "event_id": "EVT-D09-001", "clip": "Day09_EVT-D09-001_ELEVATED_RO_Skid_Controls_Walkway_20260909_015018.mp4",
    },
    {
        "date": "2026-09-09", "cam": "IPC56", "start": "10:39:19", "end": "10:41:20",
        "happened": UNIVERSAL_ALERT,
        "person": "REAL-01 (SUBJ-10)", "event_id": "EVT-D09-005", "clip": "Day09_EVT-D09-005_ELEVATED_RO_Skid_Controls_Walkway_20260909_103919.mp4",
    },
    {
        "date": "2026-09-09", "cam": "IPC56", "start": "22:01:06", "end": "22:03:06",
        "happened": UNIVERSAL_ALERT,
        "person": "REAL-01 (SUBJ-10)", "event_id": "EVT-D09-011", "clip": "Day09_EVT-D09-011_SEVERE_Ultimate_Plant_Power_Switch_20260909_220106.mp4",
    },
    {
        "date": "2026-09-11", "cam": "IPC56", "start": "06:32:37", "end": "06:34:39",
        "happened": UNIVERSAL_ALERT,
        "person": "REAL-29", "event_id": "EVT-D11-001", "clip": "Day11_EVT-D11-001_SEVERE_Ultimate_Plant_Power_Switch_20260911_063237.mp4",
    },
    {
        "date": "2026-09-11", "cam": "IPC56", "start": "09:49:20", "end": "09:51:11",
        "happened": UNIVERSAL_ALERT,
        "person": "REAL-23", "event_id": "EVT-D11-003", "clip": "Day11_EVT-D11-003_ELEVATED_RO_Skid_Controls_Walkway_20260911_094920.mp4",
    },
    {
        "date": "2026-09-11", "cam": "IPC56", "start": "14:15:46", "end": "14:18:05",
        "happened": UNIVERSAL_ALERT,
        "person": "REAL-22", "event_id": "EVT-D11-004", "clip": "Day11_EVT-D11-004_CRITICAL_Two_Multiport_Backwash_Valves_20260911_141546.mp4",
    },
    {
        "date": "2026-09-11", "cam": "IPC56", "start": "14:40:33", "end": "14:42:41",
        "happened": UNIVERSAL_ALERT,
        "person": "REAL-24", "event_id": "EVT-D11-005", "clip": "Day11_EVT-D11-005_CRITICAL_Two_Multiport_Backwash_Valves_20260911_144033.mp4",
    },
    {
        "date": "2026-09-11", "cam": "IPC56", "start": "15:30:52", "end": "15:32:54",
        "happened": UNIVERSAL_ALERT,
        "person": "REAL-04 (SUBJ-342)", "event_id": "EVT-D11-006", "clip": "Day11_EVT-D11-006_CRITICAL_Two_Multiport_Backwash_Valves_20260911_153052.mp4",
    },
    {
        "date": "2026-09-15", "cam": "IPC56", "start": "10:33:08", "end": "10:35:09",
        "happened": UNIVERSAL_ALERT,
        "person": "REAL-03", "event_id": "EVT-D15-002", "clip": "Day15_EVT-D15-002_CRITICAL_Two_Multiport_Backwash_Valves_20260915_103308.mp4",
    },
    {
        "date": "2026-09-24", "cam": "IPC56", "start": "08:10:51", "end": "08:12:52",
        "happened": UNIVERSAL_ALERT,
        "person": "REAL-01", "event_id": "EVT-D24-002", "clip": "Day24_EVT-D24-002_ELEVATED_RO_Skid_Controls_Walkway_20260924_081051.mp4",
    },
    {
        "date": "2026-09-24", "cam": "IPC56", "start": "09:26:39", "end": "09:28:58",
        "happened": UNIVERSAL_ALERT,
        "person": "REAL-01", "event_id": "EVT-D24-004", "clip": "Day24_EVT-D24-004_ELEVATED_RO_Skid_Controls_Walkway_20260924_092639.mp4",
    },
    {
        "date": "2026-09-24", "cam": "IPC56", "start": "16:14:33", "end": "16:15:01",
        "happened": UNIVERSAL_ALERT,
        "person": "REAL-01", "event_id": "EVT-D24-011", "clip": "Day24_EVT-D24-011_ELEVATED_RO_Skid_Controls_Walkway_20260924_161433.mp4",
    },
    {
        "date": "2026-09-24", "cam": "IPC56", "start": "16:38:26", "end": "16:40:28",
        "happened": UNIVERSAL_ALERT,
        "person": "REAL-01 (SUBJ-1079)", "event_id": "EVT-D24-013", "clip": "Day24_EVT-D24-013_SEVERE_Ultimate_Plant_Power_Switch_20260924_163826.mp4",
    },
    {
        "date": "2026-09-25", "cam": "IPC56", "start": "11:42:10", "end": "11:43:44",
        "happened": UNIVERSAL_ALERT,
        "person": "REAL-33", "event_id": "EVT-D25-002", "clip": "Day25_EVT-D25-002_SEVERE_Ultimate_Plant_Power_Switch_20260925_114210.mp4",
    },
    {
        "date": "2026-09-25", "cam": "IPC56", "start": "11:44:16", "end": "11:46:17",
        "happened": UNIVERSAL_ALERT,
        "person": "REAL-01", "event_id": "EVT-D25-003", "clip": "Day25_EVT-D25-003_ELEVATED_RO_Skid_Controls_Walkway_20260925_114416.mp4",
    },
    {
        "date": "2026-09-26", "cam": "IPC56", "start": "07:44:59", "end": "07:48:54",
        "happened": UNIVERSAL_ALERT,
        "person": "REAL-05", "event_id": "EVT-D26-002", "clip": "Day26_EVT-D26-002_CRITICAL_Two_Multiport_Backwash_Valves_20260926_074459.mp4",
    },
    {
        "date": "2026-09-26", "cam": "IPC56", "start": "07:49:09", "end": "07:51:23",
        "happened": UNIVERSAL_ALERT,
        "person": "REAL-07", "event_id": "EVT-D26-003", "clip": "Day26_EVT-D26-003_ELEVATED_RO_Skid_Controls_Walkway_20260926_074909.mp4",
    }
]

# Master data of all 11 unique persons involved in the 20 incidents
PERSONS_INVOLVED = [
    {
        "id": "REAL-01", "anchor": "SUBJ-10 / SUBJ-1652", "cam": "IPC56", "time": "2026-09-01 09:53:38",
        "desc": "Teal/green polo shirt, curly hair, mustache & goatee. Primary recurring operator.",
        "incidents": "8 Incidents (EVT-D01-005, EVT-D09-005, EVT-D09-011, EVT-D24-002, EVT-D24-004, EVT-D24-011, EVT-D24-013, EVT-D25-003)",
        "status": "Unregistered Subject (Pending DBGT Enrollment)",
        "crop": "REAL-01_verified_face.jpg"
    },
    {
        "id": "REAL-03", "anchor": "SUBJ-16", "cam": "IPC56", "time": "2026-09-15 10:33:08",
        "desc": "Light coloured work shirt, dark trousers. Morning shift technician.",
        "incidents": "1 Incident (EVT-D15-002)",
        "status": "Unregistered Subject (Pending DBGT Enrollment)",
        "crop": "REAL-03_verified_face.jpg"
    },
    {
        "id": "REAL-04", "anchor": "SUBJ-342", "cam": "IPC56", "time": "2026-09-11 15:30:52",
        "desc": "Light blue work shirt. Maintenance technician.",
        "incidents": "1 Incident (EVT-D11-006)",
        "status": "Unregistered Subject (Pending DBGT Enrollment)",
        "crop": "REAL-04_verified_face.jpg"
    },
    {
        "id": "REAL-05", "anchor": "SUBJ-01", "cam": "IPC56", "time": "2026-09-01 22:26:36",
        "desc": "Grey work attire, dark hair. Routine maintenance operator.",
        "incidents": "2 Incidents (EVT-D01-010, EVT-D26-002)",
        "status": "Unregistered Subject (Pending DBGT Enrollment)",
        "crop": "REAL-05_verified_face.jpg"
    },
    {
        "id": "REAL-06", "anchor": "SUBJ-03", "cam": "IPC56", "time": "2026-09-09 01:50:18",
        "desc": "Dark night vigilance attire, short hair.",
        "incidents": "1 Incident (EVT-D09-001)",
        "status": "Unregistered Subject (Pending DBGT Enrollment)",
        "crop": "REAL-06_verified_face.jpg"
    },
    {
        "id": "REAL-07", "anchor": "SUBJ-04", "cam": "IPC56", "time": "2026-09-07 07:38:27",
        "desc": "Dark casual shirt, slim build. Morning servicing operator.",
        "incidents": "2 Incidents (EVT-D07-001, EVT-D26-003)",
        "status": "Unregistered Subject (Pending DBGT Enrollment)",
        "crop": "REAL-07_verified_face.jpg"
    },
    {
        "id": "REAL-22", "anchor": "SUBJ-28", "cam": "IPC56", "time": "2026-09-11 14:15:46",
        "desc": "Casual work shirt. Afternoon technician.",
        "incidents": "1 Incident (EVT-D11-004)",
        "status": "Unregistered Subject (Pending DBGT Enrollment)",
        "crop": "REAL-22_verified_face.jpg"
    },
    {
        "id": "REAL-23", "anchor": "SUBJ-29", "cam": "IPC56", "time": "2026-09-11 09:49:20",
        "desc": "Blue work attire, short dark hair. Morning technician.",
        "incidents": "1 Incident (EVT-D11-003)",
        "status": "Unregistered Subject (Pending DBGT Enrollment)",
        "crop": "REAL-23_verified_face.jpg"
    },
    {
        "id": "REAL-24", "anchor": "SUBJ-31", "cam": "IPC56", "time": "2026-09-11 14:40:33",
        "desc": "Collared shirt, straight dark hair. Maintenance technician.",
        "incidents": "1 Incident (EVT-D11-005)",
        "status": "Unregistered Subject (Pending DBGT Enrollment)",
        "crop": "REAL-24_verified_face.jpg"
    },
    {
        "id": "REAL-29", "anchor": "SUBJ-38", "cam": "IPC56", "time": "2026-09-11 06:32:37",
        "desc": "Dark shirt, medium build. Early morning operator.",
        "incidents": "1 Incident (EVT-D11-001)",
        "status": "Unregistered Subject (Pending DBGT Enrollment)",
        "crop": "REAL-29_verified_face.jpg"
    },
    {
        "id": "REAL-33", "anchor": "SUBJ-42", "cam": "IPC56", "time": "2026-09-25 11:42:10",
        "desc": "Dark blue work attire. Midday operator.",
        "incidents": "1 Incident (EVT-D25-002)",
        "status": "Unregistered Subject (Pending DBGT Enrollment)",
        "crop": "REAL-33_verified_face.jpg"
    }
]

def build_markdown(md_path):
    md = []
    md.append("<p align=\"right\"><img src=\"thoorigai_logo.jpg\" alt=\"ThoorigAI Infotech Logo\" width=\"65\" /></p>")
    md.append("")
    md.append("# CCTV FOOTAGE REVIEW REPORT")
    md.append("## Simple Summary of Recording Issues")
    md.append("")
    md.append("| Parameter | Detail |")
    md.append("| :--- | :--- |")
    md.append("| **Client** | DBGT |")
    md.append("| **Report Date** | 2026-10-29 |")
    md.append("| **Location / Site** | RO Water Treatment Plant Rooftop Mechanical Deck |")
    md.append("| **Reviewed By** | ThoorigAI Infotech |")
    md.append("| **Report Reference** | DBGT-THOOR-2026-RO-001 |")
    md.append("")
    md.append("**Purpose:** This report explains any CCTV footage that appears to be replaced, missing, or relevant to a specific incident. Details are compiled after comprehensive forensic verification of the physical 30-day continuous archive (719.65 recorded hours from Camera `IPC56`, 99.95% coverage across 998 physical files).")
    md.append("")
    md.append("---")
    md.append("")
    
    # SECTION 1
    md.append("### 1. Video Appears to Be Replaced")
    md.append("Use this section when a recording appears to show a different day, time, or unrelated video instead of the expected footage.")
    md.append("")
    md.append("| Camera Name | Expected Date / Time | Date / Time Shown in Available Video | What Looks Wrong? | Status |")
    md.append("| :--- | :--- | :--- | :--- | :--- |")
    md.append("| IPC56 | 2026-09-27 00:00:00 to 2026-09-27 23:59:59 (Day 27) | 2026-09-26 00:00:00 to 2026-09-26 23:59:59 (Day 26) | All 33 clips in Day 27 are identical bit-for-bit file duplicates of Day 26 (matching 5,444 crops, 90.6m activity duration). Actual Sept 27 footage was substituted. | **Confirmed (Replaced / Duplicated)** |")
    md.append("")
    md.append("**Plain-language finding:**")
    md.append("Temporal bitstream, file hash, and candidate crop analysis confirmed that all 33 video segments archived under Day 27 (`2026-09-27`) are identical duplicate copies of Day 26 (`2026-09-26`). Both directories record exactly 5,444 candidate face crops and 90.6 minutes of active movement with matching presentation timestamps. This confirms that legitimate CCTV footage for Sunday, September 27 was replaced with re-dated Day 26 recordings.")
    md.append("")
    md.append("*Status guide:* **Confirmed** = supported by verification. **Suspected** = signs of a problem, but not fully proven. **Unclear** = more information is needed.")
    md.append("")
    md.append("---")
    md.append("")
    
    # SECTION 2
    md.append("### 2. Missing CCTV Footage")
    md.append("List each time period for which the expected recording could not be found.")
    md.append("")
    md.append("| Camera Name | Date | Missing From (Start Time) | Missing Until (End Time) | Approx. Duration | Root Cause / Operational Pattern |")
    md.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
    md.append("| IPC56 | 2026-09-07 (Day 07, Mon) | 09:40:14 | 09:42:40 | 2.4 mins | Automated Weekly NVR Reboot (09:40 AM) |")
    md.append("| IPC56 | 2026-09-08 (Day 08, Tue) | 14:45:37 | 15:04:23 | 18.8 mins | Inter-Clip Buffer Hitch / Plant Electrical Maintenance |")
    md.append("| IPC56 | 2026-09-14 (Day 14, Mon) | 09:40:14 | 09:42:42 | 2.4 mins | Automated Weekly NVR Reboot (09:40 AM) |")
    md.append("| IPC56 | 2026-09-20 (Day 20, Sun) | 23:42:00 | 23:43:22 | 1.4 mins | Inter-Clip Buffer Hitch |")
    md.append("| IPC56 | 2026-09-21 (Day 21, Mon) | 09:40:14 | 09:42:39 | 2.4 mins | Automated Weekly NVR Reboot (09:40 AM) |")
    md.append("| IPC56 | 2026-09-28 (Day 28, Mon) | 09:40:16 | 09:42:41 | 2.4 mins | Automated Weekly NVR Reboot (09:40 AM) |")
    md.append("")
    md.append("**Customer-friendly summary:**")
    md.append("Surveillance coverage achieved **719.65 recorded hours** across the 30-day month (**99.95% timeline coverage** across all 998 physical MP4 files). Comprehensive ground-truth verification directly against the physical master storage media confirmed that the CCTV recording maintained near-continuous uptime. Across the entire 720-hour month, **only 6 verified recording gaps occurred, totaling 29.8 minutes (0.50 hours)**:")
    md.append("1. **Automated Weekly Maintenance Reboot (4 events):** Every Monday morning at exactly 09:40 AM (Days 07, 14, 21, 28), the NVR performed a scheduled 2.4-minute maintenance reboot.")
    md.append("2. **Inter-Clip Buffer Hitches & Plant Maintenance (2 events):** Tuesday afternoon on Day 08 experienced an 18.8-minute recording interruption (14:45:37–15:04:23), and Sunday late night on Day 20 experienced a brief 1.4-minute buffer hitch (23:42:00–23:43:22).")
    md.append("*Verification Note on Day 21 Morning Block:* Forensic physical disk inspection confirmed that the previously suspected 44.9-minute morning block on Day 21 (07:17:44–08:02:40) is 100% intact and present on disk (`56_8_DBGT_IPC56_df605109..._20260921071744.mp4`, 1.06 GB, 80,920 frames). The entire 30-day archive contains zero dropped 45-minute recording blocks.")
    md.append("")
    md.append("---")
    md.append("")
    
    # SECTION 3 (UNIVERSAL ALERT NOTE + SINGLE GOOGLE DRIVE LINK + EXACT 6 COLUMNS)
    md.append("### 3. Incident Details / Person Seen")
    md.append("Use this section to describe what happened in the video. All 20 manually verified and confirmed equipment interaction incidents:")
    md.append("")
    md.append(f"> **Universal Alert Standard:** *{UNIVERSAL_ALERT}.*<br/>")
    md.append("> *Note on Event Descriptions:* Because specific component-level interaction or operational motive cannot be determined from video footage alone, all events are recorded with the standardized universal alert description above.")
    md.append("")
    md.append(f"> **Attached Google Drive Folder (All 20 Confirmed Incident Video Clips):**<br/>")
    md.append(f"> **[{SINGLE_DRIVE_LINK}]({SINGLE_DRIVE_LINK})**<br/>")
    md.append(f"> *(All 20 lossless MP4 video clips with $\\pm 60$s contextual margins are accessible in this single shared drive folder)*")
    md.append("")
    md.append("| Incident Date | Camera Name | Footage Start Time | Footage End Time | What Happened? | Person Ref. / Name (if verified) |")
    md.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
    
    for inc in INCIDENTS:
        md.append(f"| {inc['date']} | {inc['cam']} | {inc['start']} | {inc['end']} | {inc['happened']} | Unknown Subject `{inc['person']}` |")
    
    md.append("")
    md.append("---")
    md.append("")
    
    # SECTION 3.1: PERSON PHOTO / SCREENSHOT RECORD (ALL 11 PERSONS)
    md.append("#### Person Photo / Screenshot Record")
    md.append("Insert a clear CCTV screenshot below for all individuals involved in the confirmed equipment interaction incidents above. Record the camera name and exact date/time from which it was taken.")
    md.append("")
    md.append("| Photo Crop | Person Ref. | Camera Name | Screenshot Date & Time | Description / Clothing | Incidents Linked | Identification Status |")
    md.append("| :---: | :--- | :--- | :--- | :--- | :--- | :--- |")
    
    for p in PERSONS_INVOLVED:
        img_tag = f"<img src=\"person_crops/{p['crop']}\" alt=\"{p['id']}\" width=\"55\" height=\"60\" />"
        md.append(f"| {img_tag} | Unknown Subject **`{p['id']}`**<br/>*(Anchor: `{p['anchor']}`)* | {p['cam']} | {p['time']} | {p['desc']} | {p['incidents']} | {p['status']} |")
    
    md.append("")
    md.append("---")
    md.append("")
    
    # SECTION 4: OVERALL RESULT
    md.append("### 4. Overall Result")
    md.append("")
    md.append("| Issue Type | Found? | Detailed Audit Summary & Next Action |")
    md.append("| :--- | :--- | :--- |")
    md.append("| **Video replaced / suspicious video** | **YES (Confirmed)** | **Sunday Video Substitution Confirmed:** All 33 clips archived under Day 27 (`2026-09-27`) are identical bit-for-bit file duplicates of Day 26 (`2026-09-26`), matching 5,444 candidate crops and 90.6 minutes of activity. Legitimate Sunday footage was substituted with re-dated Day 26 recordings.<br/>*Next Action:* Request original physical NVR backup tapes/drive for Sept 27 to determine whether original footage was overwritten or misfiled. |")
    md.append("| **Missing footage** | **YES (Verified)** | **99.83% Timeline Coverage Maintained:** Total 7 verified recording interruptions totaling 1.25 hours (74.7 minutes) across the 720-hour month. Characterized by scheduled weekly 2.4-min NVR maintenance reboots every Monday at 09:40 AM (Days 07, 14, 21, 28), two buffer hitches (18.8m on Day 08, 1.4m on Day 20), and one 44.9-min morning gap on Day 21 (07:17–08:02). All other standard 45-minute recording segments are fully present.<br/>*Next Action:* Reconfigure Monday 09:40 AM automated reboot schedule to non-operational hours (e.g., Sunday 02:00 AM) and verify network buffer storage. |")
    md.append(f"| **Incident / person details (20 Confirmed Events)** | **YES (Verified)** | **20 Monitored Equipment Area Alert Events Confirmed:** Across 718.75 monitored hours, exactly 20 physical activity alert events were manually verified and confirmed in the monitored plant equipment deck. Due to camera angle and distance, specific component-level interaction is not definitively determined from footage alone; all 20 events represent verified physical presence and activity in the equipment deck during active surveillance periods.<br/>• **11 Unique Unregistered Personnel:** Exactly 11 individuals were photographed and visually indexed (shown in photo record above). Zero matched an enrolled employee whitelist; 100% are currently classified as Unregistered Personnel pending formal ID verification. Primary operator `REAL-01` was involved in 8 events.<br/>• **Attached Evidence:** All 20 incident clips are accessible in the single shared Google Drive folder: <a href=\"{SINGLE_DRIVE_LINK}\">{SINGLE_DRIVE_LINK}</a><br/>• **Actionable Next Steps:**<br/>1. Conduct formal identity verification with plant administration for the 11 identified individuals.<br/>2. Cross-reference plant operational logbooks against the recorded incident timestamps to verify if these activities corresponded to scheduled maintenance.<br/>3. Review the attached Google Drive incident clips for complete video evidence. |")
    md.append("")
    md.append("---")
    md.append("")
    
    # IMPORTANT NOTE & ACKNOWLEDGEMENT
    md.append("### Important Note")
    md.append("A missing recording or a video that looks different does not, by itself, prove that someone deliberately changed or deleted the footage. This report records what was observed and what could be verified from the material available.")
    md.append("")
    md.append("---")
    md.append("")
    md.append("### Acknowledgement")
    md.append("")
    md.append("| Prepared By – ThoorigAI Infotech | Reviewed / Received By – DBGT | Date |")
    md.append("| :--- | :--- | :--- |")
    md.append("| **ThoorigAI Infotech Forensic Audit Team**<br/>Surveillance Intelligence & Biometrics Division | **DBGT Facility Operations / Security Management**<br/>Facility Asset Custody Administration | **2026-10-29** |")
    md.append("")
    md.append("**CONFIDENTIAL — Prepared for DBGT by ThoorigAI Infotech**")

    Path(md_path).write_text("\n".join(md), encoding="utf-8")
    print(f"[OK] Saved Markdown report to {md_path}")

def build_pdf(pdf_path):
    styles = getSampleStyleSheet()
    custom = {}
    custom["DocTitle"] = ParagraphStyle("DocTitle", fontName="Helvetica-Bold", fontSize=15, leading=18, textColor=colors.HexColor("#0f172a"), spaceAfter=2)
    custom["DocSubTitle"] = ParagraphStyle("DocSubTitle", fontName="Helvetica-Bold", fontSize=9.5, leading=12, textColor=colors.HexColor("#0284c7"), spaceAfter=1)
    custom["H1"] = ParagraphStyle("H1", fontName="Helvetica-Bold", fontSize=10, leading=13, textColor=colors.HexColor("#0f172a"), spaceBefore=6, spaceAfter=2.5, keepWithNext=True)
    custom["H2"] = ParagraphStyle("H2", fontName="Helvetica-Bold", fontSize=8.5, leading=11, textColor=colors.HexColor("#1e293b"), spaceBefore=4, spaceAfter=2, keepWithNext=True)
    custom["Body"] = ParagraphStyle("Body", fontName="Helvetica", fontSize=7, leading=9.5, textColor=colors.HexColor("#334155"), spaceAfter=2.5)
    custom["BodyBold"] = ParagraphStyle("BodyBold", fontName="Helvetica-Bold", fontSize=7, leading=9.5, textColor=colors.HexColor("#0f172a"))
    custom["TableCell"] = ParagraphStyle("TableCell", fontName="Helvetica", fontSize=6.2, leading=8, textColor=colors.HexColor("#1e293b"))
    custom["TableCellBold"] = ParagraphStyle("TableCellBold", fontName="Helvetica-Bold", fontSize=6.2, leading=8, textColor=colors.HexColor("#0f172a"))
    custom["TableHead"] = ParagraphStyle("TableHead", fontName="Helvetica-Bold", fontSize=6.8, leading=9, textColor=colors.white)
    custom["DriveBox"] = ParagraphStyle("DriveBox", fontName="Helvetica-Bold", fontSize=6.8, leading=9, textColor=colors.HexColor("#0369a1"))

    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=38)
    story = []

    # Header / Logo
    logo_file = Path("D:/facial/team_reports/thoorigai_logo.jpg")
    if logo_file.exists():
        logo_img = RLImage(str(logo_file), width=34, height=47)
        title_flow = [
            Paragraph("CCTV FOOTAGE REVIEW REPORT", custom["DocTitle"]),
            Paragraph("Simple Summary of Recording Issues", custom["DocSubTitle"])
        ]
        head_table = Table([[title_flow, logo_img]], colWidths=[460, 63])
        head_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(head_table)
    else:
        story.append(Paragraph("CCTV FOOTAGE REVIEW REPORT", custom["DocTitle"]))
        story.append(Paragraph("Simple Summary of Recording Issues", custom["DocSubTitle"]))
    story.append(Spacer(1, 2))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284c7"), spaceAfter=4))

    # Header Meta Table
    meta_data = [
        [Paragraph("Client", custom["TableCellBold"]), Paragraph("DBGT", custom["TableCellBold"]), Paragraph("Report Date", custom["TableCellBold"]), Paragraph("2026-10-29", custom["TableCell"])],
        [Paragraph("Location / Site", custom["TableCellBold"]), Paragraph("RO Water Treatment Plant Rooftop Deck", custom["TableCell"]), Paragraph("Report Reference", custom["TableCellBold"]), Paragraph("DBGT-THOOR-2026-RO-001", custom["TableCell"])],
        [Paragraph("Reviewed By", custom["TableCellBold"]), Paragraph("ThoorigAI Infotech", custom["TableCellBold"]), Paragraph("Primary Sensor", custom["TableCellBold"]), Paragraph("Overhead 3K Camera IPC56", custom["TableCell"])],
    ]
    t_meta = Table(meta_data, colWidths=[85, 175, 85, 178])
    t_meta.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("PADDING", (0, 0), (-1, -1), 2.5),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 3))

    story.append(Paragraph(
        "<b>Purpose:</b> This report explains any CCTV footage that appears to be replaced, missing, or relevant to a specific incident. Details are compiled after comprehensive forensic verification of the physical 30-day continuous archive (719.65 recorded hours from Camera IPC56, 99.95% coverage across 998 physical files).",
        custom["Body"]
    ))

    # SECTION 1
    story.append(Paragraph("1. Video Appears to Be Replaced", custom["H1"]))
    story.append(Paragraph("Use this section when a recording appears to show a different day, time, or unrelated video instead of the expected footage.", custom["Body"]))

    rep_data = [
        [Paragraph("Camera Name", custom["TableHead"]), Paragraph("Expected Date / Time", custom["TableHead"]), Paragraph("Date / Time Shown in Video", custom["TableHead"]), Paragraph("What Looks Wrong?", custom["TableHead"]), Paragraph("Status", custom["TableHead"])],
        [Paragraph("IPC56", custom["TableCellBold"]), Paragraph("2026-09-27 (Day 27)", custom["TableCell"]), Paragraph("2026-09-26 (Day 26)", custom["TableCell"]), Paragraph("All 33 clips in Day 27 are identical bit-for-bit file duplicates of Day 26 (matching 5,444 crops, 90.6m activity duration). Actual Sept 27 footage was substituted.", custom["TableCell"]), Paragraph("<b>Confirmed (Replaced / Duplicated)</b>", custom["TableCellBold"])],
    ]
    t_rep = Table(rep_data, colWidths=[45, 110, 110, 155, 103])
    t_rep.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("PADDING", (0, 0), (-1, -1), 2.5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white]),
    ]))
    story.append(t_rep)
    story.append(Spacer(1, 2))
    story.append(Paragraph(
        "<b>Plain-language finding:</b> Temporal bitstream, file hash, and candidate crop analysis revealed that all 33 CCTV recordings archived under Day 27 (<code>2026-09-27</code>) are identical duplicate copies of Day 26 (<code>2026-09-26</code>). Both directories share identical candidate counts (5,444 crops) and 90.6 minutes of active movement. Legitimate footage for Sunday, September 27 was substituted with re-dated Day 26 recordings.<br/>"
        "<i>Status guide: Confirmed = supported by verification. Suspected = signs of a problem, but not fully proven. Unclear = more information is needed.</i>",
        custom["Body"]
    ))
    story.append(Spacer(1, 3))

    # SECTION 2
    story.append(Paragraph("2. Missing CCTV Footage", custom["H1"]))
    story.append(Paragraph("List each time period for which the expected recording could not be found.", custom["Body"]))

    miss_data = [
        [Paragraph("Camera", custom["TableHead"]), Paragraph("Date", custom["TableHead"]), Paragraph("Missing From", custom["TableHead"]), Paragraph("Missing Until", custom["TableHead"]), Paragraph("Duration", custom["TableHead"]), Paragraph("Root Cause / Operational Pattern", custom["TableHead"])],
        [Paragraph("IPC56", custom["TableCellBold"]), Paragraph("Day 07 (Mon 09-07)", custom["TableCell"]), Paragraph("09:40:14", custom["TableCell"]), Paragraph("09:42:40", custom["TableCell"]), Paragraph("2.4 mins", custom["TableCell"]), Paragraph("Automated Weekly NVR Reboot (09:40 AM)", custom["TableCell"])],
        [Paragraph("IPC56", custom["TableCellBold"]), Paragraph("Day 08 (Tue 09-08)", custom["TableCell"]), Paragraph("14:45:37", custom["TableCell"]), Paragraph("15:04:23", custom["TableCell"]), Paragraph("18.8 mins", custom["TableCell"]), Paragraph("Inter-Clip Buffer Hitch / Plant Maintenance", custom["TableCell"])],
        [Paragraph("IPC56", custom["TableCellBold"]), Paragraph("Day 14 (Mon 09-14)", custom["TableCell"]), Paragraph("09:40:14", custom["TableCell"]), Paragraph("09:42:42", custom["TableCell"]), Paragraph("2.4 mins", custom["TableCell"]), Paragraph("Automated Weekly NVR Reboot (09:40 AM)", custom["TableCell"])],
        [Paragraph("IPC56", custom["TableCellBold"]), Paragraph("Day 20 (Sun 09-20)", custom["TableCell"]), Paragraph("23:42:00", custom["TableCell"]), Paragraph("23:43:22", custom["TableCell"]), Paragraph("1.4 mins", custom["TableCell"]), Paragraph("Inter-Clip Buffer Hitch", custom["TableCell"])],
        [Paragraph("IPC56", custom["TableCellBold"]), Paragraph("Day 21 (Mon 09-21)", custom["TableCell"]), Paragraph("09:40:14", custom["TableCell"]), Paragraph("09:42:39", custom["TableCell"]), Paragraph("2.4 mins", custom["TableCell"]), Paragraph("Automated Weekly NVR Reboot (09:40 AM)", custom["TableCell"])],
        [Paragraph("IPC56", custom["TableCellBold"]), Paragraph("Day 28 (Mon 09-28)", custom["TableCell"]), Paragraph("09:40:16", custom["TableCell"]), Paragraph("09:42:41", custom["TableCell"]), Paragraph("2.4 mins", custom["TableCell"]), Paragraph("Automated Weekly NVR Reboot (09:40 AM)", custom["TableCell"])],
    ]
    t_miss = Table(miss_data, colWidths=[40, 85, 95, 95, 75, 133])
    t_miss.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("PADDING", (0, 0), (-1, -1), 2),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
    ]))
    story.append(t_miss)
    story.append(Spacer(1, 2))
    story.append(Paragraph(
        "<b>Customer-friendly summary:</b> Surveillance coverage achieved <b>719.65 recorded hours</b> across the 30-day month (<b>99.95% timeline coverage</b> across 998 physical MP4 files). Ground-truth physical drive verification confirmed <b>only 6 verified recording gaps occurred, totaling 29.8 minutes (0.50 hours)</b>: scheduled weekly 2.4-min NVR maintenance reboots every Monday at 09:40 AM (Days 07, 14, 21, 28), one plant maintenance interruption (18.8m on Day 08), and one buffer hitch (1.4m on Day 20). Physical disk verification confirmed that the previously suspected morning block on Day 21 (07:17–08:02) is 100% intact on master storage media. Zero dropped 45-minute recording blocks exist in the archive.",
        custom["Body"]
    ))
    story.append(PageBreak())

    # SECTION 3 (PAGE 2) - EXACT 6 COLUMNS OF WORD TEMPLATE + SINGLE GOOGLE DRIVE CALLOUT
    story.append(Paragraph("3. Incident Details / Person Seen (20 Confirmed Events)", custom["H1"]))
    story.append(Paragraph(
        f"<b>Universal Alert Standard:</b> <i>{UNIVERSAL_ALERT}.</i><br/>"
        "<b>Note on Event Descriptions:</b> Because specific component-level interaction or operational motive cannot be determined from video footage alone, all events are recorded with the standardized universal alert description above.",
        custom["Body"]
    ))
    
    # SINGLE DRIVE LINK CALLOUT TABLE
    drive_box_content = [
        [
            Paragraph(
                f"<b>Attached Google Drive Folder (All 20 Confirmed Incident Video Clips):</b><br/>"
                f"<a href=\"{SINGLE_DRIVE_LINK}\"><u><b>{SINGLE_DRIVE_LINK}</b></u></a><br/>"
                f"<font size=5.5 color='#475569'>All 20 lossless MP4 video clips (with ±60s contextual margins) are accessible in this single shared drive folder.</font>",
                custom["DriveBox"]
            )
        ]
    ]
    t_drive_box = Table(drive_box_content, colWidths=[523])
    t_drive_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0f9ff")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#0284c7")),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_drive_box)
    story.append(Spacer(1, 3))

    inc_data = [
        [
            Paragraph("Incident Date", custom["TableHead"]),
            Paragraph("Camera Name", custom["TableHead"]),
            Paragraph("Footage Start Time", custom["TableHead"]),
            Paragraph("Footage End Time", custom["TableHead"]),
            Paragraph("What Happened? (Universal Alert Description)", custom["TableHead"]),
            Paragraph("Person Ref. / Name (if verified)", custom["TableHead"])
        ]
    ]
    for inc in INCIDENTS:
        inc_data.append([
            Paragraph(inc["date"], custom["TableCellBold"]),
            Paragraph(inc["cam"], custom["TableCell"]),
            Paragraph(inc["start"], custom["TableCell"]),
            Paragraph(inc["end"], custom["TableCell"]),
            Paragraph(inc["happened"], custom["TableCell"]),
            Paragraph(f"<b>{inc['person']}</b>", custom["TableCellBold"]),
        ])

    t_inc = Table(inc_data, colWidths=[52, 40, 52, 52, 215, 112])
    t_inc.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("PADDING", (0, 0), (-1, -1), 1.8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(t_inc)
    story.append(PageBreak())

    # SECTION 3.1: PERSON PHOTO / SCREENSHOT RECORD (PAGE 3)
    story.append(Paragraph("Person Photo / Screenshot Record (All 11 Unique Individuals)", custom["H1"]))
    story.append(Paragraph(
        "Attached photographic face crops and forensic profiles for all 11 unique individuals involved in the 20 confirmed incidents above. All individuals are classified as Unregistered Subjects pending formal DBGT employee enrollment.",
        custom["Body"]
    ))

    photo_data = [
        [
            Paragraph("Photo", custom["TableHead"]),
            Paragraph("Person Ref.", custom["TableHead"]),
            Paragraph("Camera & Time", custom["TableHead"]),
            Paragraph("Description / Visual Features", custom["TableHead"]),
            Paragraph("Incidents Linked", custom["TableHead"]),
            Paragraph("Identification Status", custom["TableHead"])
        ]
    ]

    crops_dir = Path("d:/facial/team_reports/person_crops")
    for p in PERSONS_INVOLVED:
        crop_path = crops_dir / p["crop"]
        if crop_path.exists():
            img_obj = RLImage(str(crop_path), width=26, height=30)
        else:
            img_obj = Paragraph("No Image", custom["TableCell"])

        cam_time = f"{p['cam']}<br/>{p['time']}"
        ref_text = f"<b>{p['id']}</b><br/><font size=5 color='#64748b'>Anchor: {p['anchor']}</font>"
        photo_data.append([
            img_obj,
            Paragraph(ref_text, custom["TableCellBold"]),
            Paragraph(cam_time, custom["TableCell"]),
            Paragraph(p["desc"], custom["TableCell"]),
            Paragraph(p["incidents"], custom["TableCell"]),
            Paragraph(p["status"], custom["TableCellBold"])
        ])

    t_photo = Table(photo_data, colWidths=[32, 60, 68, 142, 115, 106])
    t_photo.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("PADDING", (0, 0), (-1, -1), 2),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 1), (0, -1), "CENTER"),
    ]))
    story.append(t_photo)
    story.append(PageBreak())

    # SECTION 4: OVERALL RESULT (PAGE 4)
    story.append(Paragraph("4. Overall Result", custom["H1"]))
    story.append(Paragraph(
        "Comprehensive audit synthesis and actionable recommendations based on empirical verification of 719.65 recorded hours, 6 footage gaps (29.8m downtime), and 20 confirmed physical incidents.",
        custom["Body"]
    ))

    overall_inc_summary = (
        "<b>20 Monitored Equipment Area Alert Events Confirmed:</b> Across 719.65 monitored hours (99.95% coverage), exactly 20 physical activity alert events were manually verified and confirmed in the monitored plant equipment deck. Due to camera angle and distance, specific component-level interaction is not definitively determined from footage alone; all 20 events represent verified physical presence and activity in the equipment deck during active surveillance periods.<br/>"
        "• <b>11 Unique Unregistered Personnel:</b> Exactly 11 individuals were photographed and visually indexed (shown in photo record on Page 3). Zero matched an enrolled employee whitelist; 100% are currently classified as Unregistered Personnel pending formal ID verification. Primary operator REAL-01 was involved in 8 events.<br/>"
        f"<b>Attached Evidence:</b> All 20 incident clips are accessible in the single shared Google Drive folder:<br/><a href=\"{SINGLE_DRIVE_LINK}\"><u><b>{SINGLE_DRIVE_LINK}</b></u></a><br/>"
        "<b>Actionable Next Steps:</b><br/>"
        "1. Conduct formal identity verification with plant administration for the 11 identified individuals.<br/>"
        "2. Cross-reference plant operational logbooks against the recorded incident timestamps to verify if these activities corresponded to scheduled maintenance.<br/>"
        "3. Review the attached Google Drive incident clips for complete video evidence."
    )

    res_data = [
        [Paragraph("Issue Type", custom["TableHead"]), Paragraph("Found?", custom["TableHead"]), Paragraph("Detailed Audit Summary & Next Action", custom["TableHead"])],
        [
            Paragraph("Video replaced / suspicious video", custom["TableCellBold"]),
            Paragraph("<b>YES (Confirmed)</b>", custom["TableCellBold"]),
            Paragraph("<b>Sunday Video Substitution Confirmed:</b> All 33 clips archived under Day 27 (<code>2026-09-27</code>) are identical bit-for-bit file duplicates of Day 26 (<code>2026-09-26</code>), matching 5,444 candidate crops and 90.6 minutes of activity. Legitimate Sunday footage was substituted with re-dated Day 26 recordings.<br/><i>Next Action:</i> Request original physical NVR backup tapes/drive for Sept 27 to determine whether original footage was overwritten or misfiled.", custom["TableCell"])
        ],
        [
            Paragraph("Missing footage", custom["TableCellBold"]),
            Paragraph("<b>YES (Verified)</b>", custom["TableCellBold"]),
            Paragraph("<b>99.83% Timeline Coverage Maintained:</b> Total 7 verified recording interruptions totaling 1.25 hours (74.7 minutes) across the 720-hour month. Characterized by scheduled weekly 2.4-min NVR maintenance reboots every Monday at 09:40 AM (Days 07, 14, 21, 28), two buffer hitches (18.8m on Day 08, 1.4m on Day 20), and one 44.9-min morning gap on Day 21 (07:17–08:02). All other standard 45-minute recording segments are fully present.<br/><i>Next Action:</i> Reconfigure Monday 09:40 AM automated reboot schedule to non-operational hours (e.g., Sunday 02:00 AM) and verify network buffer storage.", custom["TableCell"])
        ],
        [
            Paragraph("Incident / person details (20 Confirmed Events)", custom["TableCellBold"]),
            Paragraph("<b>YES (Verified)</b>", custom["TableCellBold"]),
            Paragraph(overall_inc_summary, custom["TableCell"])
        ],
    ]
    t_res = Table(res_data, colWidths=[110, 65, 348])
    t_res.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("PADDING", (0, 0), (-1, -1), 3),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(t_res)
    story.append(Spacer(1, 4))

    # Important Note
    story.append(Paragraph("<b>Important Note:</b> A missing recording or a video that looks different does not, by itself, prove that someone deliberately changed or deleted the footage. This report records what was observed and what could be verified from the material available.", custom["Body"]))
    story.append(Spacer(1, 4))

    # Acknowledgement
    story.append(Paragraph("Acknowledgement", custom["H1"]))
    ack_data = [
        [Paragraph("Prepared By – ThoorigAI Infotech", custom["TableHead"]), Paragraph("Reviewed / Received By – DBGT", custom["TableHead"]), Paragraph("Date", custom["TableHead"])],
        [Paragraph("<b>ThoorigAI Infotech Forensic Audit Team</b><br/>Surveillance Intelligence & Biometrics Division", custom["TableCell"]), Paragraph("<b>DBGT Facility Operations / Security Management</b><br/>Facility Asset Custody Administration", custom["TableCell"]), Paragraph("2026-10-29", custom["TableCell"])],
    ]
    t_ack = Table(ack_data, colWidths=[205, 218, 100])
    t_ack.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("PADDING", (0, 0), (-1, -1), 3.5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(t_ack)

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[OK] Compiled PDF report to {pdf_path}")

def main():
    # Paths
    md_out = Path("D:/facial/team_reports/05_DBGT_CCTV_Footage_Review_Report_RO_Plant.md")
    pdf_out = Path("D:/facial/team_reports/05_DBGT_CCTV_Footage_Review_Report_RO_Plant.pdf")
    brain_dir = Path("C:/Users/mkiru/.gemini/antigravity/brain/9cd9e7a5-62c1-473e-9b1f-aa014627f6c9/team_reports")
    brain_dir.mkdir(parents=True, exist_ok=True)
    brain_crops = brain_dir / "person_crops"
    brain_crops.mkdir(parents=True, exist_ok=True)

    # Copy crops to brain directory
    local_crops = Path("D:/facial/team_reports/person_crops")
    if local_crops.exists():
        for f in local_crops.glob("*.jpg"):
            shutil.copy2(f, brain_crops / f.name)
            shutil.copy2(f, brain_dir / f.name)

    build_markdown(md_out)
    build_pdf(pdf_out)

    # Sync to brain artifacts
    shutil.copy2(md_out, brain_dir / md_out.name)
    shutil.copy2(pdf_out, brain_dir / pdf_out.name)
    print(f"[OK] Synced both Markdown and PDF to brain artifacts.")

if __name__ == "__main__":
    main()
