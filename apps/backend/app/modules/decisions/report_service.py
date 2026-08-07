from __future__ import annotations

from io import BytesIO
from textwrap import shorten

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from app.modules.decisions.schemas import DecisionWorkspaceResponse


NAVY = colors.HexColor("#07101F")
PANEL = colors.HexColor("#0C192C")
TEAL = colors.HexColor("#24A99B")
RED = colors.HexColor("#B83F4B")
INK = colors.HexColor("#182536")
MUTED = colors.HexColor("#5B6B7E")
PALE = colors.HexColor("#EEF3F7")


def _safe(value: object) -> str:
    return (
        str(value or "Not recorded")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _page(canvas, doc) -> None:
    canvas.saveState()
    width, height = letter
    canvas.setFillColor(NAVY)
    canvas.rect(0, height - 0.5 * inch, width, 0.5 * inch, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(0.55 * inch, height - 0.31 * inch, "DECISIONVAULT")
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(
        width - 0.55 * inch,
        height - 0.31 * inch,
        f"Internal Decision Brief | Page {doc.page}",
    )
    canvas.setStrokeColor(colors.HexColor("#CAD5DF"))
    canvas.line(0.55 * inch, 0.52 * inch, width - 0.55 * inch, 0.52 * inch)
    canvas.setFillColor(RED)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(0.55 * inch, 0.31 * inch, "CONFIDENTIAL")
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(
        width - 0.55 * inch,
        0.31 * inch,
        "DecisionVault™, a DiscoverA.ai Technology",
    )
    canvas.restoreState()


def _styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            "ReportTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=27,
            leading=31,
            textColor=NAVY,
            alignment=TA_LEFT,
            spaceAfter=12,
        )
    )
    styles.add(
        ParagraphStyle(
            "MetricValue",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=12,
            alignment=TA_CENTER,
            textColor=INK,
        )
    )
    styles.add(
        ParagraphStyle(
            "Section",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            textColor=NAVY,
            spaceBefore=9,
            spaceAfter=9,
        )
    )
    styles.add(
        ParagraphStyle(
            "Subsection",
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=INK,
            spaceBefore=7,
            spaceAfter=5,
        )
    )
    styles.add(
        ParagraphStyle(
            "BodyDV",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=15,
            textColor=INK,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            "SmallDV",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=MUTED,
        )
    )
    styles.add(
        ParagraphStyle(
            "Critical",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=16,
            textColor=colors.HexColor("#7B1F2A"),
        )
    )
    styles.add(
        ParagraphStyle(
            "CenterSmall",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            alignment=TA_CENTER,
            textColor=INK,
        )
    )
    return styles


def _bullet_list(items: list[str], style) -> list[Paragraph]:
    return [Paragraph(f"• {_safe(item)}", style) for item in items]


def _section(title: str, items: list[str], styles) -> KeepTogether:
    content = [Paragraph(title, styles["Subsection"])]
    content.extend(_bullet_list(items or ["No items recorded."], styles["BodyDV"]))
    return KeepTogether(content)


def build_decision_brief(
    workspace: DecisionWorkspaceResponse, *, generated_by: str
) -> bytes:
    decision = workspace.decision
    analysis = decision.evidence_summary.get("demo_analysis", {})
    styles = _styles()
    output = BytesIO()
    doc = BaseDocTemplate(
        output,
        pagesize=letter,
        rightMargin=0.55 * inch,
        leftMargin=0.55 * inch,
        topMargin=0.72 * inch,
        bottomMargin=0.72 * inch,
        title=f"Decision Brief - {decision.supplier_name or decision.title}",
        author="DecisionVault, a DiscoverA.ai Technology",
        subject="Confidential internal decision intelligence brief",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="brief")
    doc.addPageTemplates(PageTemplate(id="decision-brief", frames=[frame], onPage=_page))

    story = [
        Spacer(1, 0.12 * inch),
        Paragraph("CONFIDENTIAL INTERNAL DECISION BRIEF", styles["CenterSmall"]),
        Spacer(1, 0.18 * inch),
        Paragraph(_safe(decision.supplier_name or decision.title), styles["ReportTitle"]),
        Paragraph(_safe(decision.title), styles["Subsection"]),
        Paragraph(_safe(decision.question), styles["BodyDV"]),
        Spacer(1, 0.12 * inch),
    ]

    metrics = [
        ["STATUS", "RISK", "READINESS", "CONFIDENCE"],
        [
            Paragraph(
                _safe(decision.status.replace("_", " ").upper()),
                styles["MetricValue"],
            ),
            Paragraph(decision.risk_level.upper(), styles["MetricValue"]),
            Paragraph(f"{decision.readiness_score}%", styles["MetricValue"]),
            Paragraph(f"{round(decision.confidence * 100)}%", styles["MetricValue"]),
        ],
    ]
    metric_table = Table(metrics, colWidths=[doc.width / 4] * 4)
    metric_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BACKGROUND", (0, 1), (-1, 1), PALE),
                ("TEXTCOLOR", (0, 1), (-1, 1), INK),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#C7D3DE")),
            ]
        )
    )
    story.extend([metric_table, Spacer(1, 0.18 * inch)])

    critical = list(analysis.get("critical_findings", []))
    if critical:
        critical_content = [
            Paragraph("CRITICAL SIGNAL DETECTED", styles["Critical"]),
            *_bullet_list(critical, styles["Critical"]),
        ]
        critical_table = Table([[critical_content]], colWidths=[doc.width])
        critical_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FDECEE")),
                    ("BOX", (0, 0), (-1, -1), 1.5, RED),
                    ("LEFTPADDING", (0, 0), (-1, -1), 14),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 14),
                    ("TOPPADDING", (0, 0), (-1, -1), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ]
            )
        )
        story.extend([critical_table, Spacer(1, 0.16 * inch)])

    story.extend(
        [
            Paragraph("Executive recommendation", styles["Section"]),
            Paragraph(_safe(decision.recommendation), styles["BodyDV"]),
            Paragraph(
                _safe(
                    analysis.get(
                        "accountability",
                        "DecisionVault supports accountable human review and does not make the final decision.",
                    )
                ),
                styles["SmallDV"],
            ),
            Spacer(1, 0.08 * inch),
            Paragraph("Decision profile", styles["Section"]),
        ]
    )
    profile = [
        ["Owner", _safe(decision.owner_name), "Business unit", _safe(decision.business_unit)],
        ["Category", _safe(decision.supplier_category), "Location", _safe(decision.supplier_location)],
        ["Priority", decision.priority.upper(), "Decision revision", str(decision.input_revision)],
        ["Generated by", _safe(generated_by), "Evidence records", str(len(workspace.evidence))],
    ]
    profile_table = Table(profile, colWidths=[1.0 * inch, 2.3 * inch, 1.1 * inch, 2.0 * inch])
    profile_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PALE),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("TEXTCOLOR", (0, 0), (-1, -1), INK),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CFD9E2")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.extend([profile_table, PageBreak()])

    story.extend(
        [
            Paragraph("Governed analysis", styles["ReportTitle"]),
            _section("Important facts", list(analysis.get("facts", [])), styles),
            _section("Conflicting evidence", list(analysis.get("conflicts", [])), styles),
            _section("Material risks", list(analysis.get("risks", [])), styles),
            _section("Missing information", list(analysis.get("missing_information", [])), styles),
            _section("Assumptions", list(analysis.get("assumptions", [])), styles),
            _section("Proposed controls", list(analysis.get("controls", [])), styles),
            PageBreak(),
            Paragraph("Evidence and provenance", styles["ReportTitle"]),
            Paragraph(
                "The following immutable evidence snapshots were active and authorized when this brief was generated.",
                styles["BodyDV"],
            ),
        ]
    )
    for index, evidence in enumerate(workspace.evidence, start=1):
        evidence_content = [
            Paragraph(f"[{index}] {_safe(evidence.snapshot_title)}", styles["Subsection"]),
            Paragraph(_safe(evidence.snapshot_content), styles["BodyDV"]),
            Paragraph(
                " | ".join(
                    [
                        f"Relationship: {evidence.relationship_type}",
                        f"Authority: {evidence.snapshot_authority_level}",
                        f"Trust: {round(evidence.snapshot_trust_score * 100)}%",
                        f"Source: {shorten(evidence.snapshot_source_filename or evidence.snapshot_source_locator or 'governed snapshot', width=70)}",
                    ]
                ),
                styles["SmallDV"],
            ),
        ]
        story.append(KeepTogether(evidence_content))
        story.append(Spacer(1, 0.06 * inch))

    story.extend(
        [
            PageBreak(),
            Paragraph("Accountability and disclosures", styles["ReportTitle"]),
            Paragraph("Human accountability", styles["Section"]),
            Paragraph(
                _safe(
                    analysis.get(
                        "accountability",
                        "Final approval, restriction, rejection, and publication remain human-controlled.",
                    )
                ),
                styles["BodyDV"],
            ),
            Paragraph("Report limitations", styles["Section"]),
            *_bullet_list(
                [
                    "This report is confidential and intended for internal review.",
                    "Synthetic demonstration content is labeled and must not be treated as a real merchant record.",
                    "AI-supported analysis organizes governed evidence; it does not autonomously approve, restrict, or reject.",
                    "The report reflects the Decision revision and authorized evidence available at generation time.",
                    "Recipients must preserve the access classification and handling requirements of the underlying Decision.",
                ],
                styles["BodyDV"],
            ),
            Spacer(1, 0.15 * inch),
            Paragraph("Evidence citations", styles["Section"]),
            *_bullet_list(list(analysis.get("citations", [])), styles["BodyDV"]),
            Spacer(1, 0.2 * inch),
            Paragraph(
                f"Decision ID: {_safe(decision.id)} | Revision: {decision.input_revision}",
                styles["SmallDV"],
            ),
        ]
    )
    doc.build(story)
    return output.getvalue()
