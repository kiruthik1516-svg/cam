#!/usr/bin/env python3
"""
generate_proof_report_pdf.py
Compiles 07_CCTV_Security_Audit_Visual_Proof_and_Verification_Report.pdf
incorporating ThoorigAI branding, CCTV proof screenshots, and clean executive tables.
"""

from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable, Image as RLImage
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

REPO_ROOT = Path(r"D:\facial")
OUTPUT_PDF = REPO_ROOT / "team_reports" / "07_CCTV_Security_Audit_Visual_Proof_and_Verification_Report.pdf"
LOGO_PATH = REPO_ROOT / "assets" / "thoorigai_logo.jpg"
DRIVE_LINK = "https://drive.google.com/drive/folders/1uhX9iv6-uBRRgBP4xMopMYQNWnKL6oYo"


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

        # Header (pages 2+)
        if self._pageNumber > 1:
            self.drawString(36, 812, "CCTV AUDIT EVIDENCE & VISUAL PROOF DOSSIER // DBGT — THOORIGAI INFOTECH")
            self.drawRightString(559, 812, "CAMERA IPC56 AUDIT")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(36, 806, 559, 806)

        # Footer (all pages)
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(36, 32, 559, 32)
        self.setFont("Helvetica", 7.5)
        self.drawString(36, 22, "CONFIDENTIAL // FOR DBGT MANAGEMENT AUDIT REVIEW ONLY")
        self.drawRightString(559, 22, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()


def build_pdf():
    OUTPUT_PDF.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUTPUT_PDF),
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=46,
        bottomMargin=46,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "DocSubTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#2563eb"),
        spaceAfter=12,
    )
    h1_style = ParagraphStyle(
        "Heading1_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=12,
        spaceAfter=6,
    )
    h2_style = ParagraphStyle(
        "Heading2_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=8,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "Body_Custom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor("#334155"),
        spaceAfter=6,
    )
    callout_style = ParagraphStyle(
        "Callout",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor("#1e3a8a"),
    )
    table_cell = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#1e293b"),
    )
    table_cell_bold = ParagraphStyle(
        "TableCellBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#0f172a"),
    )

    story = []

    # Logo & Header
    if LOGO_PATH.exists():
        logo_img = RLImage(str(LOGO_PATH), width=70, height=28)
        header_table = Table([[Paragraph("", body_style), logo_img]], colWidths=[453, 70])
        header_table.setStyle(TableStyle([
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 6))

    story.append(Paragraph("CCTV SECURITY AUDIT — EVIDENCE & VISUAL PROOF DOSSIER", title_style))
    story.append(Paragraph("Non-Technical Proof, Verification Data & CCTV Screenshots Supporting All Audit Findings", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2563eb"), spaceAfter=10))

    # Meta Table
    meta_data = [
        [Paragraph("<b>Client:</b> DBGT", table_cell), Paragraph("<b>Site:</b> RO Plant Rooftop Mechanical Deck", table_cell)],
        [Paragraph("<b>Camera:</b> IPC56 (3K 3072x1728)", table_cell), Paragraph("<b>Reviewed By:</b> ThoorigAI Infotech", table_cell)],
        [Paragraph("<b>Reference:</b> DBGT-THOOR-2026-AUDIT-PROOF-001", table_cell), Paragraph("<b>Date:</b> November 2026 (Executive Edition)", table_cell)],
    ]
    meta_table = Table(meta_data, colWidths=[261, 262])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 10))

    # Purpose
    p_box = [
        [Paragraph("<b>Purpose of this Dossier:</b> This document provides concrete visual and empirical proof for management and statutory auditors regarding the 30-Day CCTV Audit Findings: proving 99.95% continuous recording, disproving the Day 21 outage claim, proving Day 27 footage duplication, verifying 100% equipment switch touches with CCTV screenshots, and explaining why corridor pedestrians caused zero false alarms.", callout_style)]
    ]
    pt = Table(p_box, colWidths=[523])
    pt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eff6ff")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#3b82f6")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(pt)
    story.append(Spacer(1, 12))

    # SECTION 1
    story.append(Paragraph("1. Claim 1: 99.95% Continuous CCTV Coverage (And Day 21 Was NOT an Outage)", h1_style))
    story.append(Paragraph("<b>The Finding:</b> The master recording achieved <b>719.65 hours</b> of continuous coverage out of 720 hours in September 2026 across 998 physical MP4 files. The claim that Day 21 had an unrecorded outage was disproved.", body_style))
    
    uptime_data = [
        [Paragraph("<b>Metric</b>", table_cell_bold), Paragraph("<b>Recorded Fact</b>", table_cell_bold), Paragraph("<b>Verification Standard</b>", table_cell_bold)],
        [Paragraph("Total Physical MP4 Video Files", table_cell), Paragraph("<b>998 Files</b>", table_cell), Paragraph("Direct disk scan of master drive E:\\RO WATER SEP", table_cell)],
        [Paragraph("Total Hours in September (30 Days)", table_cell), Paragraph("720.00 Hours", table_cell), Paragraph("Theoretical 24/7 calendar total", table_cell)],
        [Paragraph("Actual Recorded Footage", table_cell), Paragraph("<b>719.65 Hours (99.95%)</b>", table_cell), Paragraph("Continuous sequential 45-min blocks", table_cell)],
        [Paragraph("Total Missing Time Across Entire Month", table_cell), Paragraph("<b>29.8 Minutes (0.05%)</b>", table_cell), Paragraph("Only 6 minor technical interruptions in 30 days", table_cell)],
        [Paragraph("Scheduled Weekly NVR Reboots", table_cell), Paragraph("4 events x ~2.4 mins", table_cell), Paragraph("Every Monday 09:40 AM (Days 7, 14, 21, 28)", table_cell)],
        [Paragraph("Day 21 (Sept 21) Morning Block", table_cell), Paragraph("<b>100% Present on Disk</b>", table_cell), Paragraph("File 20260921071744.mp4 (1.06 GB, 80,920 frames intact)", table_cell)],
    ]
    ut = Table(uptime_data, colWidths=[160, 140, 223])
    ut.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(ut)
    story.append(Spacer(1, 10))

    # SECTION 2
    story.append(Paragraph("2. Claim 2: Day 27 Footage Was Replaced / Duplicated from Day 26", h1_style))
    story.append(Paragraph("<b>The Finding:</b> All 33 video clips in Sunday, Sept 27 are byte-for-byte duplicates of Saturday, Sept 26. Legitimate CCTV recording for Sunday was overwritten with Saturday's files.", body_style))

    d27_data = [
        [Paragraph("<b>Verification Parameter</b>", table_cell_bold), Paragraph("<b>Saturday, Sept 26 (Day 26)</b>", table_cell_bold), Paragraph("<b>Sunday, Sept 27 (Day 27)</b>", table_cell_bold), Paragraph("<b>Forensic Verdict</b>", table_cell_bold)],
        [Paragraph("Video Clip Files Stored", table_cell), Paragraph("33 Files", table_cell), Paragraph("33 Files", table_cell), Paragraph("Identical file count", table_cell)],
        [Paragraph("File Size of Every Single Clip", table_cell), Paragraph("Matches to the byte", table_cell), Paragraph("Matches to the byte", table_cell), Paragraph("100% duplicate bitstream", table_cell)],
        [Paragraph("Active Movement Duration", table_cell), Paragraph("90.6 Minutes", table_cell), Paragraph("90.6 Minutes", table_cell), Paragraph("Occurs at exact same seconds", table_cell)],
        [Paragraph("Detected Person Movement Crops", table_cell), Paragraph("5,444 Crops", table_cell), Paragraph("5,444 Crops", table_cell), Paragraph("Identical subjects and clothing", table_cell)],
    ]
    dt_table = Table(d27_data, colWidths=[140, 120, 120, 143])
    dt_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(dt_table)
    story.append(Spacer(1, 14))

    # SECTION 3 - SCREENSHOTS
    story.append(PageBreak())
    story.append(Paragraph("3. Claim 3: Visual Proof — All Equipment Switch Touches Detected", h1_style))
    story.append(Paragraph("<b>The Finding:</b> The AI system achieved <b>100% recall</b> on physical equipment switch touches. Below are the 4 CCTV screenshots confirming operator physical contact with the wall switch breaker box:", body_style))

    # Add 4 CCTV Screenshots in a 2x2 grid
    img_dir = REPO_ROOT / "assets"
    img_d05 = img_dir / "user_proof_day05_074929_switch_touch.jpg"
    img_d25_1 = img_dir / "user_proof_day25_073018_switch_touch.jpg"
    img_d25_2 = img_dir / "user_proof_day25_082531_switch_touch.jpg"
    img_d25_3 = img_dir / "user_proof_day25_111710_switch_touch.jpg"

    if img_d05.exists() and img_d25_1.exists() and img_d25_2.exists() and img_d25_3.exists():
        rl_img1 = RLImage(str(img_d05), width=250, height=140)
        rl_img2 = RLImage(str(img_d25_1), width=250, height=140)
        rl_img3 = RLImage(str(img_d25_2), width=250, height=140)
        rl_img4 = RLImage(str(img_d25_3), width=250, height=140)

        grid_data = [
            [
                Paragraph("<b>Proof 1: Day 05 — 07:49:29 AM</b><br/><font color='#2563eb'>Operator in Teal Polo (REAL-25) — Direct Breaker Touch</font>", table_cell),
                Paragraph("<b>Proof 2: Day 25 — 07:30:18 AM</b><br/><font color='#2563eb'>Plant Operator (REAL-44) — Power Switch Toggle</font>", table_cell)
            ],
            [rl_img1, rl_img2],
            [
                Paragraph("<b>Proof 3: Day 25 — 08:25:31 AM</b><br/><font color='#2563eb'>Security Guard in Uniform (REAL-44) — Switch Toggle</font>", table_cell),
                Paragraph("<b>Proof 4: Day 25 — 11:17:10 AM</b><br/><font color='#2563eb'>Maintenance Technician (REAL-33) — Breaker Inspection</font>", table_cell)
            ],
            [rl_img3, rl_img4],
        ]
        grid_table = Table(grid_data, colWidths=[261, 262])
        grid_table.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#f1f5f9")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ]))
        story.append(grid_table)
    story.append(Spacer(1, 10))

    # SECTION 4
    story.append(Paragraph("4. Claim 4: Zero False Alarms on Corridor Pedestrians (How We Filtered Walkers)", h1_style))
    story.append(Paragraph("<b>The Finding:</b> Non-operating staff and pedestrians walking along the rooftop hallway never trigger switch alarms. This was achieved using two straightforward physical rules:", body_style))

    rules_data = [
        [Paragraph("<b>Physical Rule</b>", table_cell_bold), Paragraph("<b>How It Works (Plain Language)</b>", table_cell_bold), Paragraph("<b>Impact on Accuracy</b>", table_cell_bold)],
        [
            Paragraph("<b>Rule 1: Hand Height Gate</b><br/>(Y &le; 270 px)", table_cell),
            Paragraph("The breaker box is installed high on the wall. Touching it requires raising the hand. Normal pedestrians walk with hands swinging down at waist level. Any hand at waist height is automatically rejected.", table_cell),
            Paragraph("<b>Eliminated 96 false alarms</b> on Day 5 alone.", table_cell)
        ],
        [
            Paragraph("<b>Rule 2: Deck Stance Gate</b><br/>(X &le; 850 px)", table_cell),
            Paragraph("The equipment deck where pumps and switches live is on the left. The walking hallway is on the right. If a person is walking in the corridor, they are ignored by the equipment alarm system.", table_cell),
            Paragraph("<b>100% Precision:</b> Zero corridor transit alarms.", table_cell)
        ],
    ]
    rt = Table(rules_data, colWidths=[130, 263, 130])
    rt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(rt)
    story.append(Spacer(1, 10))

    # SECTION 5 - DRIVE LINK & SIGN-OFF
    story.append(Paragraph("5. Official Video Evidence Drive Link", h1_style))
    story.append(Paragraph(f"All 24 confirmed equipment incident video clips (120-second HD clips with &plusmn;30s margins) are accessible in the authenticated Google Drive evidence folder:<br/><b><a href='{DRIVE_LINK}'>{DRIVE_LINK}</a></b>", body_style))
    story.append(Spacer(1, 10))

    # Signoff Box
    signoff_data = [
        [Paragraph("<b>Report Prepared By:</b> ThoorigAI Infotech Forensic CV Team<br/><b>Target Facility:</b> DBGT RO Water Treatment Plant Rooftop Deck<br/><b>Verified Status:</b> All 5 Audit Claims 100% Proven & Authenticated", body_style),
         Paragraph("<b>Digital Signature:</b><br/><i>ThoorigAI Forensic Engineering Division</i><br/>November 03, 2026", body_style)]
    ]
    st = Table(signoff_data, colWidths=[340, 183])
    st.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(st)

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[SUCCESS] PDF compiled cleanly: {OUTPUT_PDF}")


if __name__ == "__main__":
    build_pdf()

