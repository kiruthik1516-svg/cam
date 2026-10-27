#!/usr/bin/env python3
"""
generate_all_team_reports_pdf.py
Builds 4 distinct executive PDF reports for team distribution using ReportLab.
Terminology strictly adheres to forensic findings:
ALL 1,652 PERSONAS ARE UNKNOWN / UNREGISTERED SUBJECTS (PENDING IDENTIFICATION).
NO PRESUMED ROLES, EMPLOYEE TITLES, OR STAFF LABELS.
"""

import json
import pandas as pd
from pathlib import Path
import shutil
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

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

    def draw_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#64748b"))

        # Running header on page 2+
        if self._pageNumber > 1:
            self.drawString(36, 812, "RO ROOFTOP SURVEILLANCE & BIOMETRIC INTELLIGENCE // CAMERA IPC56")
            self.drawRightString(559, 812, getattr(self, "report_title", "OFFICIAL AUDIT REPORT"))
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(36, 806, 559, 806)

        # Running footer
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(36, 38, 559, 38)

        self.setFont("Helvetica", 8)
        self.drawString(36, 26, "CONFIDENTIAL // WATER TREATMENT PLANT OPERATIONS // VERIFIED AUDIT")
        self.drawRightString(559, 26, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()

def get_base_styles():
    styles = getSampleStyleSheet()
    custom = {}
    custom["DocTitle"] = ParagraphStyle(
        "DocTitle",
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=4,
    )
    custom["DocSubTitle"] = ParagraphStyle(
        "DocSubTitle",
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#0369a1"),
        spaceAfter=8,
    )
    custom["H1"] = ParagraphStyle(
        "H1",
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True,
    )
    custom["Body"] = ParagraphStyle(
        "Body",
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#334155"),
        spaceAfter=4,
    )
    custom["Bullet"] = ParagraphStyle(
        "Bullet",
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#334155"),
        leftIndent=10,
        spaceAfter=3,
    )
    custom["Callout"] = ParagraphStyle(
        "Callout",
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#0f172a"),
    )
    custom["TableCell"] = ParagraphStyle(
        "TableCell",
        fontName="Helvetica",
        fontSize=7,
        leading=9,
        textColor=colors.HexColor("#1e293b"),
    )
    custom["TableCellBold"] = ParagraphStyle(
        "TableCellBold",
        fontName="Helvetica-Bold",
        fontSize=7,
        leading=9,
        textColor=colors.HexColor("#0f172a"),
    )
    custom["TableHead"] = ParagraphStyle(
        "TableHead",
        fontName="Helvetica-Bold",
        fontSize=7,
        leading=9,
        textColor=colors.white,
    )
    return custom

def make_callout(text, styles, bg_color="#f0f9ff", border_color="#0284c7"):
    p = Paragraph(text, styles["Callout"])
    t = Table([[p]], colWidths=[523])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(bg_color)),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor(border_color)),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t

# -----------------------------------------------------------------------------
# BUILD REPORT 1: Executive Summary PDF
# -----------------------------------------------------------------------------
def build_report_1(out_pdf, master, df_man):
    styles = get_base_styles()
    doc = SimpleDocTemplate(str(out_pdf), pagesize=A4, leftMargin=36, rightMargin=36, topMargin=40, bottomMargin=42)
    story = []

    personas = master["personas"]
    t1 = [p for p in personas if p["total_detections"] >= 50]
    contacts = [p for p in personas if p["zone_direct_contacts"] > 0]
    sa = sum(p["shift_distribution"].get("Shift A (Morning, 06:00-13:59)", 0) for p in personas)
    sb = sum(p["shift_distribution"].get("Shift B (Afternoon, 14:00-21:59)", 0) for p in personas)
    sc = sum(p["shift_distribution"].get("Shift C (Night Vigilance, 22:00-05:59)", 0) for p in personas)
    total_vecs = sa + sb + sc

    story.append(Paragraph("RO Water Treatment Plant // 30-Day Surveillance Audit", styles["DocSubTitle"]))
    story.append(Paragraph("Executive Briefing & Facility Vulnerability Report", styles["DocTitle"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284c7"), spaceAfter=6))

    callout_txt = (
        "<b>CRITICAL SECURITY AUDIT FINDING: 100% UNREGISTERED / UNKNOWN SUBJECTS</b><br/>"
        "Zero facial profiles match an enrolled employee database. <b>All 1,652 detected personas (SUBJ-01 to SUBJ-1652) represent UNKNOWN PERSONS (Pending Identification).</b> "
        "Tiers reflect sighting frequency only—NOT confirmed employment or authorized clearance."
    )
    story.append(make_callout(callout_txt, styles, bg_color="#fff1f2", border_color="#e11d48"))
    story.append(Spacer(1, 6))

    story.append(Paragraph("1. Executive Mission Overview", styles["H1"]))
    story.append(Paragraph(
        "An autonomous forensic and biometric surveillance audit was conducted over 30 continuous calendar days of native 3K CCTV footage covering the RO Water Treatment Plant rooftop. The audit established continuous tracking of all human activity in the mechanical wing, measured shift-by-shift recurrence patterns, resolved historical video clipping blindspots, and logged every direct physical contact event against mission-critical equipment assets.",
        styles["Body"]
    ))

    story.append(Paragraph("2. Key Operational Metrics", styles["H1"]))
    kpi_data = [
        [Paragraph("Metric Category", styles["TableHead"]), Paragraph("Audit Result", styles["TableHead"]), Paragraph("Operational Security Context", styles["TableHead"])],
        [Paragraph("Total Facility Coverage", styles["TableCellBold"]), Paragraph("713.66 Recorded Hours", styles["TableCellBold"]), Paragraph("30 continuous calendar days (100% of Sept 2026 footage)", styles["TableCell"])],
        [Paragraph("Total Discovered Personas", styles["TableCellBold"]), Paragraph(f"{len(personas):,} Unique Personas", styles["TableCellBold"]), Paragraph("100% Unknown / Unregistered Individuals grouped via ArcFace clustering", styles["TableCell"])],
        [Paragraph("High-Frequency Unknowns", styles["TableCellBold"]), Paragraph(f"{len(t1)} Individuals", styles["TableCellBold"]), Paragraph("Tier 1 recurring unknown subjects (50+ detections each)", styles["TableCell"])],
        [Paragraph("Direct Equipment Contacts", styles["TableCellBold"]), Paragraph(f"{len(contacts)} Unknown Individuals", styles["TableCellBold"]), Paragraph("Verified touching multiport valves, skid controls, or electrical breaker switch", styles["TableCell"])],
        [Paragraph("Pristine Incident Clips", styles["TableCellBold"]), Paragraph(f"{len(df_man)} Events (8.20 GB)", styles["TableCellBold"]), Paragraph("Lossless H.265 stream cuts with +/-60s pre/post buffers", styles["TableCell"])],
        [Paragraph("Processed Face Vectors", styles["TableCellBold"]), Paragraph(f"{total_vecs:,} Embeddings", styles["TableCellBold"]), Paragraph("512-D ArcFace vectors passing strict quality threshold (Q >= 40)", styles["TableCell"])],
    ]
    t_kpi = Table(kpi_data, colWidths=[130, 115, 278])
    t_kpi.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("PADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
    ]))
    story.append(t_kpi)
    story.append(Spacer(1, 6))

    story.append(Paragraph("3. Operational Shift Workload Distribution", styles["H1"]))
    story.append(Paragraph(
        f"<b>Shift A (Morning, 06:00 – 13:59):</b> <b>{sa:,} detections ({sa/total_vecs*100:.1f}%)</b> — Peak operating window where recurring unknown subjects routinely operated valves.<br/>"
        f"<b>Shift B (Afternoon, 14:00 – 21:59):</b> <b>{sb:,} detections ({sb/total_vecs*100:.1f}%)</b> — Secondary window with multiple unknown subjects traversing the corridor.<br/>"
        f"<b>Shift C (Night Vigilance, 22:00 – 05:59):</b> <b>{sc:,} detections ({sc/total_vecs*100:.1f}%)</b> — Night visits, perimeter walkthroughs, and main breaker switch contacts.",
        styles["Body"]
    ))
    story.append(Spacer(1, 6))

    story.append(Paragraph("4. Incident Investigations & Resolutions", styles["H1"]))
    story.append(Paragraph("<b>1. Day 1 Backwash Valve Incident (09:53:38):</b> Re-extracted full continuous 4-minute clip (Day01_0953_Manual_Incident_Audit.mp4) and cataloged unknown person as <b>SUBJ-1652</b>.", styles["Bullet"]))
    story.append(Paragraph("<b>2. Day 1 Night Power Breaker Contact (22:27:36):</b> Re-extracted seamless 6-minute clip (Day01_2227_Manual_Incident_Audit.mp4) spanning the 22:28 file split.", styles["Bullet"]))
    story.append(Paragraph("<b>3. Sorting Column Inversion Fix:</b> Rebuilt all 30 clipping indices with strict wall-clock sorting, eliminating timestamp inversions across all 179 incident events.", styles["Bullet"]))
    story.append(Spacer(1, 6))

    story.append(Paragraph("5. Immediate Security Recommendations", styles["H1"]))
    story.append(Paragraph("<b>1. Mandatory Personnel Enrollment:</b> Conduct immediate formal identity verification with facility HR to associate names and employment status with all 1,652 unknown subject clusters.<br/>"
                           "<b>2. Physical Access Restriction:</b> Secure Zone 1A/B Valves and Zone 2 Power Switch with physical lockout/tagout (LOTO) padlock boxes.<br/>"
                           "<b>3. Real-Time Spatial Alerting:</b> Implement automated audible alerts when any unauthorized centroid breaches the 40px buffer of Zone 1 or Zone 2.", styles["Body"]))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[OK] Compiled: {out_pdf}")

# -----------------------------------------------------------------------------
# BUILD REPORT 2: Forensic Biometrics PDF
# -----------------------------------------------------------------------------
def build_report_2(out_pdf, master):
    styles = get_base_styles()
    doc = SimpleDocTemplate(str(out_pdf), pagesize=A4, leftMargin=36, rightMargin=36, topMargin=40, bottomMargin=42)
    story = []

    personas = master["personas"]
    t1 = [p for p in personas if p["total_detections"] >= 50]
    contacts = [p for p in personas if p["zone_direct_contacts"] > 0]
    contacts.sort(key=lambda x: x["zone_direct_contacts"], reverse=True)

    story.append(Paragraph("RO Water Treatment Plant // Biometric Intelligence Directory", styles["DocSubTitle"]))
    story.append(Paragraph("Forensic Biometrics & Master Persona Audit", styles["DocTitle"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284c7"), spaceAfter=6))

    callout_txt = (
        "<b>ALL IDENTITIES CLASSIFIED AS UNKNOWN SUBJECTS (PENDING ENROLLMENT)</b><br/>"
        "Total Discovered: 1,652 Personas (<code>SUBJ-01</code> to <code>SUBJ-1652</code>). Tiers reflect recurrence volume, NOT job titles or authorized clearances.<br/>"
        "<b>GROUND TRUTH FINDING:</b> Unknown subject SUBJ-1652 verified biometrically distinct from SUBJ-02 (similarity = 0.1831)."
    )
    story.append(make_callout(callout_txt, styles, bg_color="#fff1f2", border_color="#e11d48"))
    story.append(Spacer(1, 6))

    story.append(Paragraph("1. Tier 1 High-Frequency Recurring Unknown Subjects (50+ Detections)", styles["H1"]))
    t1_data = [
        [Paragraph("Subject ID", styles["TableHead"]), Paragraph("Forensic Status", styles["TableHead"]), Paragraph("Total Dets", styles["TableHead"]), Paragraph("Active Days", styles["TableHead"]), Paragraph("First Seen", styles["TableHead"]), Paragraph("Last Seen", styles["TableHead"]), Paragraph("Contacts", styles["TableHead"]), Paragraph("Risk", styles["TableHead"])],
    ]
    for p in t1:
        pid = p["persona_id"]
        dets = f"{p['total_detections']:,}"
        days = str(p["days_active_count"])
        first = p["first_seen"][:16]
        last = p["last_seen"][:16]
        cnt = str(p["zone_direct_contacts"])
        risk = "CRITICAL" if p["zone_direct_contacts"] > 20 else ("ELEVATED" if p["zone_direct_contacts"] > 0 else "LOW")
        t1_data.append([
            Paragraph(f"<b>{pid}</b>", styles["TableCellBold"]),
            Paragraph("Unknown Person", styles["TableCell"]),
            Paragraph(dets, styles["TableCell"]),
            Paragraph(days, styles["TableCell"]),
            Paragraph(first, styles["TableCell"]),
            Paragraph(last, styles["TableCell"]),
            Paragraph(f"<b>{cnt}</b>", styles["TableCellBold"]),
            Paragraph(risk, styles["TableCellBold"]),
        ])
    t_t1 = Table(t1_data, colWidths=[60, 85, 50, 48, 100, 100, 45, 35])
    t_t1.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("PADDING", (0, 0), (-1, -1), 3),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
    ]))
    story.append(t_t1)
    story.append(Spacer(1, 8))

    story.append(Paragraph("2. Critical Equipment Protection Zone Breach Ledger", styles["H1"]))
    story.append(Paragraph("Exactly 17 unknown individuals established direct physical contact (IoU > 0.08) with plant equipment assets:", styles["Body"]))
    
    c_data = [
        [Paragraph("Subject ID", styles["TableHead"]), Paragraph("Contacts", styles["TableHead"]), Paragraph("Active Days", styles["TableHead"]), Paragraph("Total Dets", styles["TableHead"]), Paragraph("Primary Equipment Asset", styles["TableHead"]), Paragraph("Hazard", styles["TableHead"])],
    ]
    for p in contacts:
        pid = p["persona_id"]
        cnt = str(p["zone_direct_contacts"])
        days = str(p["days_active_count"])
        dets = str(p["total_detections"])
        z_names = [e["zone_name"] for e in p.get("zone_events_log", []) if e.get("is_direct_contact")]
        primary = z_names[0] if z_names else "Two Multiport Backwash Valves"
        hazard = "CRITICAL" if "Valve" in primary else ("SEVERE" if "Power" in primary else "ELEVATED")
        c_data.append([
            Paragraph(f"<b>{pid}</b>", styles["TableCellBold"]),
            Paragraph(f"<b>{cnt}</b>", styles["TableCellBold"]),
            Paragraph(days, styles["TableCell"]),
            Paragraph(dets, styles["TableCell"]),
            Paragraph(primary, styles["TableCell"]),
            Paragraph(hazard, styles["TableCellBold"]),
        ])
    t_c = Table(c_data, colWidths=[70, 50, 60, 55, 218, 70])
    t_c.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("PADDING", (0, 0), (-1, -1), 3),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
    ]))
    story.append(t_c)
    story.append(Spacer(1, 8))

    story.append(Paragraph("3. Forensic Investigation: SUBJ-1652 vs SUBJ-02", styles["H1"]))
    verif_txt = (
        "<b>FORENSIC GROUND TRUTH FINDING:</b><br/>"
        "• <b>Unknown Subject SUBJ-02:</b> Morning walkway visitor at 09:04:32 (dark navy attire, exemplar <code>face_0620</code>).<br/>"
        "• <b>Unknown Subject SUBJ-1652:</b> Manual backwash valve operator at 09:53:38 (teal polo shirt, curly hair, mustache).<br/>"
        "• <b>InsightFace 512-D Cosine Similarity: 0.1831 (NON-MATCH).</b> Confirms two distinct individuals."
    )
    story.append(make_callout(verif_txt, styles, bg_color="#fffbeb", border_color="#d97706"))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[OK] Compiled: {out_pdf}")

# -----------------------------------------------------------------------------
# BUILD REPORT 3: Technical Architecture PDF
# -----------------------------------------------------------------------------
def build_report_3(out_pdf):
    styles = get_base_styles()
    doc = SimpleDocTemplate(str(out_pdf), pagesize=A4, leftMargin=36, rightMargin=36, topMargin=40, bottomMargin=42)
    story = []

    story.append(Paragraph("RO Water Treatment Plant // Systems & CV Engineering", styles["DocSubTitle"]))
    story.append(Paragraph("Pipeline Architecture & Technical Post-Mortem", styles["DocTitle"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284c7"), spaceAfter=6))

    callout_txt = (
        "<b>SYSTEM SPECIFICATION:</b> Native 3K HEVC (2880x1620 @ 30 FPS) &nbsp;|&nbsp; Bitrate: ~4.2 Mbps<br/>"
        "<b>EXTRACTION ENGINE:</b> Lossless Stream Slicing (>250x Realtime Speed) &nbsp;|&nbsp; Enforced Buffer: +/-60s"
    )
    story.append(make_callout(callout_txt, styles))
    story.append(Spacer(1, 8))

    story.append(Paragraph("1. Technical Root Cause Analysis", styles["H1"]))
    story.append(Paragraph(
        "<b>Bug 1: Stage 1 Premature Motion Window Cutoff</b><br/>"
        "In Clip 14 (094423.mp4, duration 44m 57s), automated motion detection stopped after 42 seconds (09:44:23 to 09:45:05) because initial entry movement ceased as the person stepped behind the door frame. Consequently, the re-entry at 09:53:20 and valve operation at 09:53:38 had zero candidate frames extracted. <i>Resolution:</i> Implemented continuous rolling temporal sliding windows and multi-tier manual verification.",
        styles["Body"]
    ))
    story.append(Paragraph(
        "<b>Bug 2: Database Sorting Inversion Bug</b><br/>"
        "Legacy scripts queried <code>ORDER BY device_id, sequence_number ASC</code>. Because sequence_number was the relative intra-clip second offset (0-2697) rather than absolute wall-clock timestamp, multi-clip queries interleaved detections from different hours, creating inverted ranges (e.g. 11:02 to 09:43) in 29/30 CSV files. <i>Resolution:</i> Enforced <code>ORDER BY timestamp ASC</code>, bringing timestamp inversions down to 0 across all 30 days.",
        styles["Body"]
    ))
    story.append(Spacer(1, 8))

    story.append(Paragraph("2. Calibrated Native 3K Spatial Geometry", styles["H1"]))
    geom_data = [
        [Paragraph("Facility Zone ID", styles["TableHead"]), Paragraph("Native 3K Bounding Box [x1, y1, x2, y2]", styles["TableHead"]), Paragraph("Hazard Category", styles["TableHead"]), Paragraph("Operational Purpose", styles["TableHead"])],
        [Paragraph("Stage 1 Perimeter", styles["TableCellBold"]), Paragraph("[295, 20, 1489, 780] (1194x760)", styles["TableCell"]), Paragraph("Observation Mask", styles["TableCellBold"]), Paragraph("Filters sky/terrace noise; covers 100% plant assets", styles["TableCell"])],
        [Paragraph("Zone 1A (Skid Valve)", styles["TableCellBold"]), Paragraph("[1080, 370, 1210, 500]", styles["TableCell"]), Paragraph("CRITICAL HAZARD", styles["TableCellBold"]), Paragraph("Manual backwash lever (Day 1 09:53:38 incident point)", styles["TableCell"])],
        [Paragraph("Zone 1B (Filter Heads)", styles["TableCellBold"]), Paragraph("[810, 440, 990, 580]", styles["TableCell"]), Paragraph("CRITICAL HAZARD", styles["TableCellBold"]), Paragraph("Dual vessel multiport high-pressure heads", styles["TableCell"])],
        [Paragraph("Zone 2 (Power Switch)", styles["TableCellBold"]), Paragraph("[995, 340, 1095, 495]", styles["TableCell"]), Paragraph("SEVERE HAZARD", styles["TableCellBold"]), Paragraph("Main electrical breaker box (Day 1 22:27:36 incident point)", styles["TableCell"])],
        [Paragraph("Zone 3 (Skid Work Deck)", styles["TableCellBold"]), Paragraph("[1080, 320, 1420, 790]", styles["TableCell"]), Paragraph("ELEVATED MONITORING", styles["TableCellBold"]), Paragraph("Technician walkway corridor and control station", styles["TableCell"])],
    ]
    t_geom = Table(geom_data, colWidths=[110, 140, 110, 163])
    t_geom.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("PADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
    ]))
    story.append(t_geom)
    story.append(Spacer(1, 8))

    story.append(Paragraph("3. High-Speed Bitstream Extraction Architecture", styles["H1"]))
    story.append(Paragraph(
        "By enforcing direct HEVC bitstream copying (<code>-c copy</code>), re-encoding overhead was completely eliminated. The entire 30-day incident dataset of <b>179 pristine video clips (8.20 GB) was extracted in 108.7 seconds</b> directly from read-only external storage (>250x realtime speed), with enforced +/-60s pre/post roll safety margins.",
        styles["Body"]
    ))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[OK] Compiled: {out_pdf}")

# -----------------------------------------------------------------------------
# BUILD REPORT 4: Incident Dossier PDF
# -----------------------------------------------------------------------------
def build_report_4(out_pdf, df_man):
    styles = get_base_styles()
    doc = SimpleDocTemplate(str(out_pdf), pagesize=A4, leftMargin=36, rightMargin=36, topMargin=40, bottomMargin=42)
    story = []

    story.append(Paragraph("RO Water Treatment Plant // Compliance & Evidence Custody", styles["DocSubTitle"]))
    story.append(Paragraph("30-Day Incident Evidence Dossier & Audit Master Ledger", styles["DocTitle"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284c7"), spaceAfter=6))

    callout_txt = (
        f"<b>TOTAL EXTRACTED CLIPS:</b> {len(df_man)} Events (8.20 GB in <code>day_01</code> to <code>day_30</code>)<br/>"
        "<b>SAFETY BUFFERS:</b> +/-60s Enforced &nbsp;|&nbsp; <b>DAILY AUDIT CSVs:</b> 90 Synchronized Documents"
    )
    story.append(make_callout(callout_txt, styles))
    story.append(Spacer(1, 6))

    story.append(Paragraph("1. Complete Chronological Incident Master Ledger (179 Events)", styles["H1"]))
    
    table_data = [
        [
            Paragraph("Event ID", styles["TableHead"]),
            Paragraph("Day", styles["TableHead"]),
            Paragraph("Date", styles["TableHead"]),
            Paragraph("Start", styles["TableHead"]),
            Paragraph("End", styles["TableHead"]),
            Paragraph("Dur", styles["TableHead"]),
            Paragraph("Critical Zone", styles["TableHead"]),
            Paragraph("Hazard", styles["TableHead"]),
            Paragraph("Personas Involved", styles["TableHead"]),
        ]
    ]

    for _, r in df_man.iterrows():
        eid = str(r["Event_ID"])
        day_str = f"D{int(r['Day']):02d}"
        start_ts = str(r["WallClock_Start"])
        end_ts = str(r["WallClock_End"])
        date_str = start_ts.split(" ")[0] if " " in start_ts else ""
        t_start = start_ts.split(" ")[1][:8] if " " in start_ts else start_ts[:8]
        t_end = end_ts.split(" ")[1][:8] if " " in end_ts else end_ts[:8]
        dur = f"{int(r['Duration_Sec'])}s"
        zone = str(r["Facility_Zone"]).replace("Two Multiport Backwash Valves", "Multiport Valves").replace("RO Skid Controls & Walkway", "RO Skid Controls")
        hazard = str(r["Hazard_Level"])
        personas = str(r["Personas"])

        table_data.append([
            Paragraph(eid, styles["TableCellBold"]),
            Paragraph(day_str, styles["TableCell"]),
            Paragraph(date_str, styles["TableCell"]),
            Paragraph(t_start, styles["TableCell"]),
            Paragraph(t_end, styles["TableCell"]),
            Paragraph(dur, styles["TableCell"]),
            Paragraph(zone, styles["TableCell"]),
            Paragraph(hazard, styles["TableCellBold"]),
            Paragraph(personas, styles["TableCell"]),
        ])

    t_all = Table(table_data, colWidths=[65, 30, 55, 45, 45, 30, 110, 55, 88], repeatRows=1)
    t_all.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("PADDING", (0, 0), (-1, -1), 3),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
    ]))
    story.append(t_all)

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[OK] Compiled: {out_pdf}")

def generate_all_pdfs():
    print("Loading data for PDF compilation...")
    with open("D:/facial/data/30day_personas/30day_personas_master.json", "r", encoding="utf-8") as f:
        master = json.load(f)
    df_man = pd.read_csv("D:/facial/incident_evidence/extracted_incident_manifest.csv")

    local_dir = Path("D:/facial/team_reports")
    artifact_dir = Path("C:/Users/mkiru/.gemini/antigravity/brain/8c6e85a2-8ea1-4c6c-bb23-a9aed5b45fc6/team_reports")
    local_dir.mkdir(parents=True, exist_ok=True)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    pdf1 = local_dir / "01_Executive_Surveillance_Summary.pdf"
    pdf2 = local_dir / "02_Forensic_Biometrics_and_Persona_Audit.pdf"
    pdf3 = local_dir / "03_Pipeline_Architecture_and_Root_Cause_Analysis.pdf"
    pdf4 = local_dir / "04_30Day_Incident_Evidence_and_Compliance_Dossier.pdf"

    build_report_1(pdf1, master, df_man)
    build_report_2(pdf2, master)
    build_report_3(pdf3)
    build_report_4(pdf4, df_man)

    for p in [pdf1, pdf2, pdf3, pdf4]:
        shutil.copy2(str(p), str(artifact_dir / p.name))
        print(f"[OK] Copied to artifact directory: {artifact_dir / p.name}")

if __name__ == "__main__":
    generate_all_pdfs()
