"""Polished PDF renderer for the Portfolio Risk-O-Meter."""

from __future__ import annotations

import math
from pathlib import Path
from xml.sax.saxutils import escape

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Wedge
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    Flowable,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


NAVY = colors.HexColor("#172033")
RED = colors.HexColor("#D10A0A")
LIGHT_BG = colors.HexColor("#F4F5F7")
CARD_BORDER = colors.HexColor("#E5E7EB")
MUTED = colors.HexColor("#64748B")
YELLOW = colors.HexColor("#F8C400")

LEVEL_COLORS = {
    "Very Low": "#0B7A43",
    "Low": "#42A54A",
    "Moderate": "#F4C430",
    "High": "#F58220",
    "Very High": "#EF3434",
}


class DashboardCanvas(Canvas):
    """Adds the dashboard background, header, and footer to every page."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_states: list[dict] = []

    def showPage(self) -> None:
        self._saved_states.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        page_count = len(self._saved_states)
        for state in self._saved_states:
            self.__dict__.update(state)
            self._decorate(page_count)
            super().showPage()
        super().save()

    def _decorate(self, page_count: int) -> None:
        width, height = A4
        self.saveState()
        self.setFillColor(NAVY)
        self.rect(0, height - 12 * mm, width, 12 * mm, fill=1, stroke=0)
        self.setFillColor(colors.white)
        self.setFont("Helvetica-Bold", 8)
        self.drawString(15 * mm, height - 7.5 * mm, "PORTFOLIO ANALYTICS")
        self.setFillColor(colors.HexColor("#CBD5E1"))
        self.setFont("Helvetica", 7)
        self.drawRightString(width - 15 * mm, height - 7.5 * mm, "Explainable Risk-O-Meter")
        self.setStrokeColor(colors.HexColor("#D8DCE2"))
        self.line(15 * mm, 12 * mm, width - 15 * mm, 12 * mm)
        self.setFillColor(MUTED)
        self.setFont("Helvetica", 7)
        self.drawString(15 * mm, 7.5 * mm, "Portfolio Risk-O-Meter")
        self.drawRightString(width - 15 * mm, 7.5 * mm, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()


class RoundedCard(Flowable):
    """A rounded white card behind a single child flowable."""

    def __init__(self, child: Flowable, width: float, padding: float = 10):
        super().__init__()
        self.child = child
        self.card_width = width
        self.padding = padding
        self.child_width = width - 2 * padding

    def wrap(self, available_width: float, available_height: float) -> tuple[float, float]:
        _, child_height = self.child.wrap(self.child_width, available_height)
        self.height = child_height + 2 * self.padding
        return self.card_width, self.height

    def draw(self) -> None:
        self.canv.saveState()
        self.canv.setFillColor(colors.HexColor("#D9DCE1"))
        self.canv.roundRect(1.5, -1.5, self.card_width, self.height, 8, fill=1, stroke=0)
        self.canv.setFillColor(colors.white)
        self.canv.setStrokeColor(CARD_BORDER)
        self.canv.roundRect(0, 0, self.card_width, self.height, 8, fill=1, stroke=1)
        self.child.drawOn(self.canv, self.padding, self.padding)
        self.canv.restoreState()


def _risk_gauge(score: float, level: str, output: Path) -> None:
    """Create a high-resolution segmented semicircular risk gauge."""

    fig, ax = plt.subplots(figsize=(8.4, 4.6), dpi=180)
    fig.patch.set_alpha(0)
    ax.set_aspect("equal")
    ax.axis("off")

    segments = [
        (144, 180, "#087443", "VERY LOW"),
        (108, 144, "#42A54A", "LOW"),
        (72, 108, "#F4C430", "MODERATE"),
        (36, 72, "#F58220", "HIGH"),
        (0, 36, "#EF3434", "VERY HIGH"),
    ]
    for start, end, color, label in segments:
        ax.add_patch(Wedge((0, 0), 1.0, start, end, width=0.27, color=color, ec="white", lw=2))
        angle = math.radians((start + end) / 2)
        x, y = 0.86 * math.cos(angle), 0.86 * math.sin(angle)
        rotation = (start + end) / 2 - 90
        ax.text(
            x, y, label, ha="center", va="center", rotation=rotation,
            rotation_mode="anchor", fontsize=7.2, fontweight="bold", color="white",
        )

    for tick in range(0, 101, 10):
        angle = math.radians(180 - tick * 1.8)
        outer = (0.69 * math.cos(angle), 0.69 * math.sin(angle))
        inner = (0.64 * math.cos(angle), 0.64 * math.sin(angle))
        ax.plot([inner[0], outer[0]], [inner[1], outer[1]], color="#64748B", lw=0.7)
        if tick % 20 == 0:
            ax.text(
                0.58 * math.cos(angle), 0.58 * math.sin(angle), str(tick),
                ha="center", va="center", fontsize=6.5, color="#475569",
            )

    needle_angle = math.radians(180 - score * 1.8)
    needle_length = 0.63
    ax.plot(
        [0, needle_length * math.cos(needle_angle)],
        [0, needle_length * math.sin(needle_angle)],
        color="#555B66", lw=4, solid_capstyle="round", zorder=5,
    )
    ax.add_patch(Circle((0, 0), 0.055, color="#555B66", zorder=6))
    ax.text(0, -0.18, f"{score:.0f}", ha="center", va="center", fontsize=22, fontweight="bold", color="#172033")
    ax.text(
        0, -0.34, f"{level.upper()} RISK", ha="center", va="center",
        fontsize=10, fontweight="bold", color=LEVEL_COLORS[level],
    )
    ax.set_xlim(-1.08, 1.08)
    ax.set_ylim(-0.42, 1.08)
    plt.tight_layout(pad=0)
    fig.savefig(output, transparent=True, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)


def _score_bar(score: float, level: str) -> Table:
    filled = max(1, min(10, round(score / 10)))
    cells = [["" for _ in range(10)]]
    table = Table(cells, colWidths=[8] * 10, rowHeights=[6])
    commands = [
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#E5E7EB")),
        ("BOX", (0, 0), (-1, -1), 0.2, colors.white),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.white),
    ]
    commands.append(("BACKGROUND", (0, 0), (filled - 1, 0), colors.HexColor(LEVEL_COLORS[level])))
    table.setStyle(TableStyle(commands))
    return table


def build_riskometer_story(
    analysis: dict,
    doc_width: float,
    output_dir: Path,
) -> list[Flowable]:
    """Build Risk-O-Meter pages for either the unified or standalone report."""

    output_dir.mkdir(parents=True, exist_ok=True)
    gauge_path = output_dir / "riskometer_gauge.png"
    _risk_gauge(analysis["overall_score"], analysis["overall_level"], gauge_path)

    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "DashboardTitle", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=22, leading=26, textColor=NAVY, alignment=0, spaceAfter=3,
    )
    section = ParagraphStyle(
        "DashboardSection", parent=styles["Heading2"], fontName="Helvetica-Bold",
        fontSize=13, leading=16, textColor=RED, spaceAfter=6,
    )
    body = ParagraphStyle(
        "RiskBody", parent=styles["BodyText"], fontName="Helvetica",
        fontSize=8.5, leading=12, textColor=colors.HexColor("#334155"),
    )
    small = ParagraphStyle(
        "RiskSmall", parent=body, fontSize=7.2, leading=9.5, textColor=MUTED,
    )
    score_style = ParagraphStyle(
        "BigScore", parent=body, fontName="Helvetica-Bold", fontSize=20,
        leading=22, alignment=1, textColor=colors.HexColor(LEVEL_COLORS[analysis["overall_level"]]),
    )
    level_style = ParagraphStyle(
        "Level", parent=body, fontName="Helvetica-Bold", fontSize=9,
        alignment=1, textColor=colors.HexColor(LEVEL_COLORS[analysis["overall_level"]]),
    )
    overview = Table(
        [[
            [
                Paragraph("Overall Portfolio Risk", small),
                Paragraph(f"{analysis['overall_score']:.2f}", score_style),
                Paragraph(f"{escape(analysis['overall_level'].upper())} RISK", level_style),
            ],
            [
                Paragraph("Portfolio Value Analysed", small),
                Paragraph(f"Rs. {analysis['total_value']:,.2f}", ParagraphStyle(
                    "Value", parent=body, fontName="Helvetica-Bold", fontSize=15, leading=20, textColor=NAVY
                )),
                Paragraph("Seven independent measurable risk modules", small),
            ],
        ]],
        colWidths=[79 * mm, 79 * mm],
    )
    overview.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEAFTER", (0, 0), (0, 0), 0.6, CARD_BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))

    gauge_content = Table(
        [
            [Paragraph("Portfolio Risk Meter", section)],
            [Table([[""]], colWidths=[158 * mm], rowHeights=[0.5], style=[("BACKGROUND", (0, 0), (-1, -1), CARD_BORDER)])],
            [Image(str(gauge_path), width=145 * mm, height=79 * mm)],
        ],
        colWidths=[160 * mm],
    )
    gauge_content.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))

    story: list[Flowable] = [
        Paragraph("Portfolio Risk-O-Meter", title),
        Paragraph("A transparent view of concentration, quality, liquidity and market risk.", small),
        Spacer(1, 8),
        RoundedCard(overview, doc_width),
        Spacer(1, 10),
        RoundedCard(gauge_content, doc_width),
        PageBreak(),
        Paragraph("Risk Module Scorecard", section),
    ]

    rows: list[list] = [[
        Paragraph("<b>Risk Type</b>", body),
        Paragraph("<b>Score</b>", body),
        Paragraph("<b>Level</b>", body),
        Paragraph("<b>Risk Scale</b>", body),
        Paragraph("<b>Coverage</b>", body),
    ]]
    for result in analysis["results"]:
        level_color = LEVEL_COLORS[result.level]
        rows.append([
            Paragraph(f"<b>{escape(result.name.replace('_', ' ').title())}</b>", body),
            Paragraph(f"<b>{result.score:.2f}</b>", body),
            Paragraph(f"<font color='{level_color}'><b>{escape(result.level)}</b></font>", body),
            _score_bar(result.score, result.level),
            Paragraph(escape(result.coverage), small),
        ])
    rows.append([
        Paragraph("<b>Overall Portfolio Risk</b>", body),
        Paragraph(f"<b>{analysis['overall_score']:.2f}</b>", body),
        Paragraph(
            f"<font color='{LEVEL_COLORS[analysis['overall_level']]}'><b>{escape(analysis['overall_level'])}</b></font>",
            body,
        ),
        _score_bar(analysis["overall_score"], analysis["overall_level"]),
        Paragraph("Weighted score", small),
    ])
    scorecard = Table(
        rows, colWidths=[43 * mm, 17 * mm, 25 * mm, 45 * mm, 30 * mm],
        repeatRows=1,
    )
    scorecard.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#FFF3F3")),
        ("TEXTCOLOR", (0, 0), (-1, 0), RED),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#F1F5F9")),
        ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#E2E8F0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 1), (2, -1), "CENTER"),
        ("ALIGN", (3, 1), (3, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#FAFAFB")]),
    ]))
    story.extend([RoundedCard(scorecard, doc_width), PageBreak()])

    for result in analysis["results"]:
        detail_rows = [
            [
                Paragraph(f"<b>{result.score:.2f}</b>", ParagraphStyle(
                    f"{result.name}Score", parent=score_style,
                    textColor=colors.HexColor(LEVEL_COLORS[result.level]),
                )),
                Paragraph(
                    f"<font color='{LEVEL_COLORS[result.level]}'><b>{escape(result.level.upper())} RISK</b></font><br/>"
                    f"<font color='#64748B'>Coverage: {escape(result.coverage)}</font>",
                    body,
                ),
            ],
            [
                Paragraph("<b>Calculated values</b>", body),
                Paragraph(escape("  |  ".join(f"{key}: {value}" for key, value in result.values.items())), body),
            ],
            [Paragraph("<b>Formula</b>", body), Paragraph(escape(result.formula), body)],
            [Paragraph("<b>Why this score?</b>", body), Paragraph(escape(result.explanation), body)],
        ]
        detail_table = Table(detail_rows, colWidths=[38 * mm, 120 * mm])
        detail_table.setStyle(TableStyle([
            ("SPAN", (0, 0), (0, 0)),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LINEBELOW", (0, 0), (-1, 0), 0.5, CARD_BORDER),
            ("LINEBELOW", (0, 1), (-1, -2), 0.35, colors.HexColor("#EEF0F3")),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]))
        story.extend([
            KeepTogether([
                Paragraph(f"{result.name.replace('_', ' ').title()} Risk", section),
                RoundedCard(detail_table, doc_width),
                Spacer(1, 11),
            ])
        ])

    story.extend([
        Spacer(1, 4),
        Paragraph(
            "Methodology note: Scores and module weights are configurable in riskometer_config.json. "
            "The Risk-O-Meter is an analytical indicator based on available portfolio, market, "
            "fundamental and NIFTY 50 data; it is not investment advice.",
            small,
        ),
    ])
    return story


def generate_riskometer_pdf(analysis: dict, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(output), pagesize=A4, rightMargin=14 * mm, leftMargin=14 * mm,
        topMargin=18 * mm, bottomMargin=17 * mm,
    )
    story = build_riskometer_story(analysis, doc.width, output.parent)
    doc.build(story, canvasmaker=DashboardCanvas)
