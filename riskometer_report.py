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
        fontSize=13, leading=16, textColor=colors.HexColor("#0E8290"), spaceAfter=6,
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
    compact = ParagraphStyle(
        "RiskCompact", parent=body, fontSize=6.2, leading=7.6,
        textColor=colors.HexColor("#334155"),
    )
    compact_muted = ParagraphStyle(
        "RiskCompactMuted", parent=compact, fontSize=5.6, leading=6.8, textColor=MUTED,
    )
    compact_header = ParagraphStyle(
        "RiskCompactHeader", parent=compact, fontName="Helvetica-Bold",
        fontSize=6.4, leading=7.5, textColor=NAVY,
    )

    overview = Table(
        [[
            [
                Paragraph("Overall risk", compact_muted),
                Paragraph(f"{analysis['overall_score']:.2f}", score_style),
                Paragraph(f"{escape(analysis['overall_level'].upper())} RISK", level_style),
            ],
            [
                Paragraph("Portfolio value analysed", compact_muted),
                Paragraph(f"Rs. {analysis['total_value']:,.0f}", ParagraphStyle(
                    "CompactValue", parent=compact, fontName="Helvetica-Bold",
                    fontSize=12, leading=15, textColor=NAVY,
                )),
                Paragraph("Seven measurable modules", compact_muted),
            ],
        ]],
        colWidths=[doc_width * 0.155, doc_width * 0.155],
    )
    overview.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEAFTER", (0, 0), (0, 0), 0.5, CARD_BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    gauge_panel = Table(
        [
            [Paragraph("Portfolio Risk Meter", section)],
            [overview],
            [Image(str(gauge_path), width=doc_width * 0.29, height=doc_width * 0.155)],
        ],
        colWidths=[doc_width * 0.32],
    )
    gauge_panel.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))

    rows: list[list] = [[
        Paragraph("Risk module", compact_header),
        Paragraph("Score", compact_header),
        Paragraph("Level", compact_header),
        Paragraph("Risk scale", compact_header),
        Paragraph("Coverage", compact_header),
    ]]
    for result in analysis["results"]:
        rows.append([
            Paragraph(escape(result.name.replace("_", " ").title()), compact_header),
            Paragraph(f"<b>{result.score:.2f}</b>", compact),
            Paragraph(
                f"<font color='{LEVEL_COLORS[result.level]}'><b>{escape(result.level)}</b></font>",
                compact,
            ),
            _score_bar(result.score, result.level),
            Paragraph(escape(result.coverage), compact_muted),
        ])
    rows.append([
        Paragraph("Overall portfolio risk", compact_header),
        Paragraph(f"<b>{analysis['overall_score']:.2f}</b>", compact),
        Paragraph(
            f"<font color='{LEVEL_COLORS[analysis['overall_level']]}'><b>{escape(analysis['overall_level'])}</b></font>",
            compact,
        ),
        _score_bar(analysis["overall_score"], analysis["overall_level"]),
        Paragraph("Weighted score", compact_muted),
    ])
    scorecard_width = doc_width * 0.62
    scorecard = Table(
        rows,
        colWidths=[
            scorecard_width * 0.22,
            scorecard_width * 0.10,
            scorecard_width * 0.13,
            scorecard_width * 0.22,
            scorecard_width * 0.33,
        ],
    )
    scorecard.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF3F6")),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#F1F5F9")),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#E2E8F0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 1), (3, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3.2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.2),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#FAFAFB")]),
    ]))
    scorecard_panel = Table(
        [[Paragraph("Risk Module Scorecard", section)], [scorecard]],
        colWidths=[scorecard_width],
    )
    scorecard_panel.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))

    top_dashboard = Table(
        [[RoundedCard(gauge_panel, doc_width * 0.34, padding=7), RoundedCard(scorecard_panel, doc_width * 0.64, padding=7)]],
        colWidths=[doc_width * 0.35, doc_width * 0.65],
    )
    top_dashboard.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (0, 0), 0),
        ("RIGHTPADDING", (0, 0), (0, 0), 6),
        ("LEFTPADDING", (1, 0), (1, 0), 6),
        ("RIGHTPADDING", (1, 0), (1, 0), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    cards_per_row = 4
    card_width = doc_width * (0.98 / cards_per_row)
    explanation_cards = []
    for result in analysis["results"]:
        card_text = (
            f"<b>{escape(result.name.replace('_', ' ').title())} - {result.score:.2f} "
            f"<font color='{LEVEL_COLORS[result.level]}'>{escape(result.level)}</font></b><br/>"
            f"{escape(result.explanation)}<br/>"
            f"<font color='#64748B'>Coverage: {escape(result.coverage)}</font>"
        )
        card = Table([[Paragraph(card_text, compact)]], colWidths=[card_width])
        card.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ("BOX", (0, 0), (-1, -1), 0.45, CARD_BORDER),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        explanation_cards.append(card)
    while len(explanation_cards) % cards_per_row:
        explanation_cards.append(Spacer(1, 1))
    explanation_rows = [
        explanation_cards[index:index + cards_per_row]
        for index in range(0, len(explanation_cards), cards_per_row)
    ]
    explanations = Table(
        explanation_rows,
        colWidths=[card_width] * cards_per_row,
        hAlign="LEFT",
    )
    explanations.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))

    return [
        Paragraph(
            "RISK ANALYSIS",
            ParagraphStyle("RiskKicker", parent=small, fontName="Helvetica-Bold", fontSize=7, textColor=colors.HexColor("#0E8290"), spaceAfter=2),
        ),
        Paragraph("Portfolio Risk-O-Meter", title),
        Paragraph("One-page view of the overall meter, complete module scorecard, and explanation of every score.", small),
        Spacer(1, 5),
        top_dashboard,
        Spacer(1, 5),
        Paragraph("What drives each score", section),
        explanations,
        Spacer(1, 3),
        Paragraph(
            "Methodology note: configurable analytical indicators based on available portfolio, market, "
            "fundamental and NIFTY 50 data; not investment advice.",
            compact_muted,
        ),
    ]


def generate_riskometer_pdf(analysis: dict, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(output), pagesize=A4, rightMargin=14 * mm, leftMargin=14 * mm,
        topMargin=18 * mm, bottomMargin=17 * mm,
    )
    story = build_riskometer_story(analysis, doc.width, output.parent)
    doc.build(story, canvasmaker=DashboardCanvas)
