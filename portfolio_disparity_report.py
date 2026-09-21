"""PDF section builder for Disparity Impact Analysis -- a since-inception
comparison of the portfolio against Nifty 50, Nifty Midcap 150 and Nifty 500:
a return bar chart, an opportunity-loss table (in percentage points and
rupees), and a risk/return statistics table. Mirrors the
build_riskometer_story() / build_style_story() pattern."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Flowable, Image, KeepTogether, Paragraph, Spacer, Table, TableStyle
from xml.sax.saxutils import escape

HEADING_RED = colors.HexColor("#123A63")
MUTED = colors.HexColor("#64748B")
NAVY = colors.HexColor("#123A63")
BORDER = colors.HexColor("#D9E2EC")
POSITIVE = colors.HexColor("#16A34A")
NEGATIVE = colors.HexColor("#DC2626")

SERIES_ORDER = ["Portfolio", "Nifty 50", "Nifty Midcap 150", "Nifty 500"]

STAT_ROWS = [
    ("annualized_return_pct", "Average Annualized Return", "pct"),
    ("avg_monthly_return_pct", "Average Monthly Return", "pct"),
    ("best_month_pct", "Best Month", "pct"),
    ("worst_month_pct", "Worst Month", "pct_paren"),
    ("worst_3day_return_pct", "Worst 3-Day Return", "pct_paren"),
    ("std_dev_pct", "Standard Deviation", "pct"),
    ("sharpe_ratio", "Sharpe Ratio", "ratio"),
    ("pct_winning_months", "% Winning Months", "pct"),
    ("pct_losing_months", "% Losing Months", "pct"),
]


def _format_inr(value: float) -> str:
    return f"Rs. {value:,.0f}"


def _fmt(value, kind: str) -> str:
    if value is None or value != value:
        return "N/A"
    if kind == "pct":
        return f"{value:.2f}"
    if kind == "pct_paren":
        return f"({abs(value):.2f})" if value < 0 else f"{value:.2f}"
    if kind == "amount_paren":
        return f"({abs(value):,.2f})" if value < 0 else f"{value:,.2f}"
    if kind == "ratio":
        return f"{value:.2f}"
    return str(value)


def _return_chart(labels: list[str], values: list[float], output: Path) -> None:
    fig, ax = plt.subplots(figsize=(5.6, 2.5), dpi=180)
    fig.patch.set_facecolor("white")

    positions = np.arange(len(labels))
    plotted = [0.0 if v != v else v for v in values]
    bars = ax.bar(positions, plotted, width=0.55, color="#123A63", zorder=3)
    for bar, value in zip(bars, values):
        label = "N/A" if value != value else f"{value:.2f}"
        ax.text(
            bar.get_x() + bar.get_width() / 2, bar.get_height(), label,
            ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#172033", zorder=5,
        )

    ax.set_xticks(positions)
    ax.set_xticklabels(labels, fontsize=8, color="#334155")
    ax.set_ylabel("% Return", fontsize=8.5, color="#64748B")
    finite_values = [v for v in values if v == v]
    top = max(finite_values + [1]) * 1.2
    bottom = min(finite_values + [0]) * 1.2 if min(finite_values + [0]) < 0 else 0
    ax.set_ylim(bottom, top)
    ax.axhline(0, color="#94A3B8", linewidth=0.8)
    ax.grid(axis="y", color="#E2E8F0", linewidth=0.7, zorder=0)
    ax.grid(axis="x", visible=False)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda value, _pos: f"{value:,.0f}"))
    for spine in ["top", "right", "left"]:
        ax.spines[spine].set_visible(False)
    ax.tick_params(axis="both", labelsize=7.5, colors="#64748B")

    plt.tight_layout()
    fig.savefig(output, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def build_disparity_story(
    disparity: dict,
    doc_width: float,
    output_dir: Path,
    benchmark_names: list[str] | None = None,
) -> list[Flowable]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "DisparityTitle", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=20, leading=24, alignment=0, textColor=HEADING_RED, spaceAfter=4,
    )
    section = ParagraphStyle(
        "DisparitySection", parent=styles["Heading2"], fontName="Helvetica-Bold",
        fontSize=12, leading=15, textColor=colors.HexColor("#0E8290"), spaceAfter=4,
    )
    small = ParagraphStyle(
        "DisparitySmall", parent=styles["BodyText"], fontName="Helvetica",
        fontSize=7.2, leading=10, textColor=MUTED,
    )
    kicker = ParagraphStyle(
        "DisparityKicker", parent=small, fontName="Helvetica-Bold", fontSize=7,
        textColor=colors.HexColor("#0E8290"), spaceAfter=2,
    )
    header_left = ParagraphStyle("DHeaderLeft", parent=small, fontName="Helvetica-Bold", fontSize=7.2, leading=9, textColor=colors.white, alignment=TA_LEFT)
    header_right = ParagraphStyle("DHeaderRight", parent=header_left, alignment=TA_RIGHT)
    header_center = ParagraphStyle("DHeaderCenter", parent=header_left, alignment=TA_CENTER)
    cell_left = ParagraphStyle("DCellLeft", parent=small, fontSize=7.2, leading=9, textColor=colors.HexColor("#1F2937"), alignment=TA_LEFT)
    cell_right = ParagraphStyle("DCellRight", parent=cell_left, alignment=TA_RIGHT)
    cell_center = ParagraphStyle("DCellCenter", parent=cell_left, alignment=TA_CENTER)

    series_names = ["Portfolio"] + (benchmark_names if benchmark_names is not None else SERIES_ORDER[1:])
    series = disparity["series"]
    opportunity_loss = disparity["opportunity_loss"]

    since_text = disparity["since_date"].strftime("%d %b %Y")
    as_of_text = disparity["as_of_date"].strftime("%d %b %Y")
    invested_amount = disparity["invested_amount"]

    left_width = doc_width * 0.38
    right_width = doc_width * 0.59

    # ----- Left: Portfolio Benchmark table + return chart -----
    left_column = [Paragraph("Portfolio Benchmark", section)]
    benchmark_rows = [[
        Paragraph("Series", header_left),
        Paragraph(f"% Return ({since_text} till date)", header_right),
    ]]
    for name in series_names:
        benchmark_rows.append([
            Paragraph(escape(name), cell_left),
            Paragraph(_fmt(series.get(name, {}).get("return_pct"), "pct"), cell_right),
        ])
    benchmark_table = Table(benchmark_rows, colWidths=[left_width * 0.62, left_width * 0.38])
    benchmark_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]))
    left_column.append(benchmark_table)
    left_column.append(Spacer(1, 3))

    chart_path = output_dir / "disparity_return_chart.png"
    _return_chart(series_names, [series.get(name, {}).get("return_pct", float("nan")) for name in series_names], chart_path)
    left_column.append(Image(str(chart_path), width=left_width, height=left_width * (2.5 / 5.6)))

    # ----- Right: Opportunity Loss table -----
    right_column = [Paragraph("Opportunity Loss", section)]
    loss_rows = [[
        Paragraph("Portfolio vs.", header_left),
        Paragraph("%", header_right),
        Paragraph("Amount (Rs.)", header_right),
    ]]
    for name in series_names[1:]:
        entry = opportunity_loss.get(name, {"disparity_pct": float("nan"), "amount": float("nan")})
        pct = entry["disparity_pct"]
        amount = entry["amount"]
        pct_style = cell_right if pct != pct else ParagraphStyle("DLossPct", parent=cell_right, textColor=(NEGATIVE if pct < 0 else POSITIVE))
        amount_style = cell_right if amount != amount else ParagraphStyle("DLossAmt", parent=cell_right, textColor=(NEGATIVE if amount < 0 else POSITIVE))
        loss_rows.append([
            Paragraph(f"{escape(name)} Return -Since Inception", cell_left),
            Paragraph(_fmt(pct, "pct_paren"), pct_style),
            Paragraph(_fmt(amount, "amount_paren"), amount_style),
        ])
    loss_table = Table(loss_rows, colWidths=[right_width * 0.56, right_width * 0.20, right_width * 0.24])
    loss_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    right_column.append(loss_table)
    right_column.append(Spacer(1, 6))
    right_column.append(Paragraph(
        f"Opportunity loss values a lumpsum of {_format_inr(invested_amount)} -- equal to the "
        "portfolio's current value -- invested instead in each benchmark since inception. Figures "
        "in brackets mean the portfolio underperformed that benchmark.",
        small,
    ))

    top_columns = Table(
        [[left_column, right_column]],
        colWidths=[left_width, right_width],
        hAlign="LEFT",
    )
    top_columns.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (0, 0), 0),
        ("RIGHTPADDING", (0, 0), (0, 0), 16),
        ("LEFTPADDING", (1, 0), (1, 0), 16),
        ("RIGHTPADDING", (1, 0), (1, 0), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("LINEBEFORE", (1, 0), (1, 0), 0.5, BORDER),
    ]))

    # ----- Bottom: Key Statistics table -----
    stats_header = [Paragraph("Key Statistics", header_left)] + [
        Paragraph(escape(name), header_center) for name in series_names
    ]
    stats_rows = [stats_header]
    for stat_key, stat_label, kind in STAT_ROWS:
        row = [Paragraph(stat_label, cell_left)]
        for name in series_names:
            stats = series.get(name, {}).get("stats")
            value = stats.get(stat_key) if stats else None
            row.append(Paragraph(_fmt(value, kind), cell_center))
        stats_rows.append(row)

    stat_col_count = len(series_names)
    label_width = doc_width * 0.26
    stat_col_width = (doc_width - label_width) / stat_col_count
    stats_table = Table(
        stats_rows, colWidths=[label_width] + [stat_col_width] * stat_col_count, repeatRows=1,
    )
    stats_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 1.8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.8),
    ]))

    story = [
        Paragraph("PERFORMANCE ANALYSIS", kicker),
        Paragraph("Disparity Impact Analysis", title_style),
        Paragraph(
            f"Portfolio Date: {as_of_text}. Comparison window: {since_text} till date -- the earliest "
            "date for which every currently-held stock has price history, used as a proxy for "
            "\"since inception\" since the analyzer only knows today's holdings and quantities, not "
            "when they were purchased. ETFs are excluded; only equity holdings are considered.",
            small,
        ),
        Spacer(1, 3),
        top_columns,
        Spacer(1, 4),
        stats_table,
    ]
    return [KeepTogether(story)]
