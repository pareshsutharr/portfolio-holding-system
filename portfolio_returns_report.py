"""PDF section builder for Portfolio Returns vs Benchmarks, mirroring the
build_riskometer_story() / build_style_story() pattern."""

from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

NAVY = colors.HexColor("#0F172A")
HEADING_RED = colors.HexColor("#D10A0A")
BORDER = colors.HexColor("#D9E2EC")
MUTED = colors.HexColor("#64748B")
POSITIVE = colors.HexColor("#16A34A")
NEGATIVE = colors.HexColor("#DC2626")


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "ReturnsTitle", parent=base["Title"], fontName="Helvetica-Bold",
            fontSize=20, leading=24, alignment=TA_LEFT, textColor=HEADING_RED, spaceAfter=4,
        ),
        "section": ParagraphStyle(
            "ReturnsSection", parent=base["Heading2"], fontName="Helvetica-Bold",
            fontSize=13, leading=16, textColor=HEADING_RED, spaceAfter=6,
        ),
        "small": ParagraphStyle(
            "ReturnsSmall", parent=base["BodyText"], fontName="Helvetica",
            fontSize=7.2, leading=10, textColor=MUTED,
        ),
        "header": ParagraphStyle(
            "ReturnsHeader", parent=base["BodyText"], fontName="Helvetica-Bold",
            fontSize=7.5, leading=9, alignment=TA_CENTER, textColor=colors.white,
        ),
        "cell": ParagraphStyle(
            "ReturnsCell", parent=base["BodyText"], fontName="Helvetica",
            fontSize=7.5, leading=9, alignment=TA_CENTER, textColor=colors.HexColor("#1F2937"),
        ),
        "cell_left": ParagraphStyle(
            "ReturnsCellLeft", parent=base["BodyText"], fontName="Helvetica-Bold",
            fontSize=7.5, leading=9, alignment=TA_LEFT, textColor=colors.HexColor("#1F2937"),
        ),
    }


def _pct_cell(value, positive_style, negative_style, na_style):
    if value is None or value != value:
        return Paragraph("N/A", na_style)
    style = positive_style if value >= 0 else negative_style
    sign = "+" if value >= 0 else ""
    return Paragraph(f"{sign}{value * 100:.2f}%", style)


def _drawdown_cell(value, style, na_style):
    if value is None or value != value:
        return Paragraph("N/A", na_style)
    return Paragraph(f"-{value * 100:.2f}%", style)


def _metric_table(rows, benchmark_names, styles, metric_key, cell_fn, doc_width):
    header = [Paragraph("Series", styles["header"])]
    header += [Paragraph(escape(row["period"]), styles["header"]) for row in rows]
    table_rows = [header]

    series_names = ["Portfolio"] + benchmark_names
    for series_name in series_names:
        key = "portfolio" if series_name == "Portfolio" else series_name
        cells = [Paragraph(escape(series_name), styles["cell_left"])]
        cells += [cell_fn(row[f"{key}_{metric_key}"]) for row in rows]
        table_rows.append(cells)

    column_count = len(rows) + 1
    col_widths = [doc_width / column_count] * column_count
    table = Table(table_rows, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return table


def build_returns_story(returns_analysis, doc_width, output_dir=None):
    styles = _styles()
    rows = returns_analysis["rows"]
    benchmark_names = returns_analysis["benchmark_names"]
    as_of = returns_analysis["as_of_date"]
    as_of_text = as_of.strftime("%d %b %Y") if as_of is not None else "N/A"

    positive = ParagraphStyle("ReturnsPositive", parent=styles["cell"], textColor=POSITIVE, fontName="Helvetica-Bold")
    negative = ParagraphStyle("ReturnsNegative", parent=styles["cell"], textColor=NEGATIVE, fontName="Helvetica-Bold")
    not_available = ParagraphStyle("ReturnsNA", parent=styles["cell"], textColor=MUTED)
    drawdown_style = ParagraphStyle("ReturnsDrawdown", parent=styles["cell"], textColor=NEGATIVE, fontName="Helvetica-Bold")

    story = [
        Paragraph("Portfolio Returns vs Benchmarks", styles["title"]),
        Paragraph(
            "Absolute return and maximum drawdown of the current portfolio "
            "(same holdings, same quantities as today) had it been held for "
            "the trailing 3 months, 6 months, 1 year and 3 years, compared "
            "against the Nifty 50, Nifty Midcap 150 and Nifty 500 indices "
            "over the same windows. ETFs are excluded; only equity holdings "
            "are considered.",
            styles["small"],
        ),
        Paragraph(f"Prices as of {as_of_text}.", styles["small"]),
        Spacer(1, 10),
        Paragraph("Absolute Return", styles["section"]),
        _metric_table(
            rows, benchmark_names, styles, "return",
            lambda v: _pct_cell(v, positive, negative, not_available), doc_width,
        ),
        Spacer(1, 14),
        Paragraph("Maximum Drawdown", styles["section"]),
        Paragraph("Largest peak-to-trough decline within each window.", styles["small"]),
        Spacer(1, 4),
        _metric_table(
            rows, benchmark_names, styles, "drawdown",
            lambda v: _drawdown_cell(v, drawdown_style, not_available), doc_width,
        ),
        Spacer(1, 8),
    ]

    coverage_text = "  |  ".join(
        f"{row['period']}: {row['coverage_percent']:.1f}% of equity value covered" for row in rows
    )
    story.append(Paragraph(coverage_text, styles["small"]))

    start_dates = returns_analysis.get("benchmark_start_dates", {})
    if start_dates:
        history_text = "  |  ".join(
            f"{name} history from {date.strftime('%d %b %Y')}" for name, date in start_dates.items()
        )
        story.append(Paragraph(
            f"{history_text}. A period longer than a benchmark's available history shows N/A.",
            styles["small"],
        ))

    return story
