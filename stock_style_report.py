"""PDF section builder for Stock Style Classification, mirroring the
build_riskometer_story() pattern in riskometer_report.py."""

from pathlib import Path
from xml.sax.saxutils import escape

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    Flowable,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from charts import create_donut_chart

NAVY = colors.HexColor("#0F172A")
ACCENT = colors.HexColor("#1D4ED8")
HEADING_RED = colors.HexColor("#D10A0A")
BORDER = colors.HexColor("#D9E2EC")
MUTED = colors.HexColor("#64748B")

STYLE_COLORS = {
    "growth": "#16A34A",
    "value": "#1D4ED8",
    "momentum": "#F58220",
    "quality": "#7C3AED",
    "Unclassified": "#94A3B8",
}

STYLE_HIGHLIGHT_COLORS = {
    "growth": "#DCFCE7",
    "value": "#DBEAFE",
    "momentum": "#FFEDD5",
    "quality": "#EDE9FE",
}

RATING_COLORS = {
    "Exceptional": "#0B7A43",
    "Very Strong": "#42A54A",
    "Strong": "#84A98C",
    "Moderate": "#F4C430",
    "Average": "#F58220",
    "Weak": "#EF6C34",
    "Very Weak": "#EF3434",
    "Unclassified": "#94A3B8",
}


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "StyleTitle", parent=base["Title"], fontName="Helvetica-Bold",
            fontSize=20, leading=24, alignment=TA_LEFT, textColor=HEADING_RED, spaceAfter=4,
        ),
        "section": ParagraphStyle(
            "StyleSection", parent=base["Heading2"], fontName="Helvetica-Bold",
            fontSize=13, leading=16, textColor=HEADING_RED, spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "StyleBody", parent=base["BodyText"], fontName="Helvetica",
            fontSize=8.5, leading=12, textColor=colors.HexColor("#334155"),
        ),
        "small": ParagraphStyle(
            "StyleSmall", parent=base["BodyText"], fontName="Helvetica",
            fontSize=7.2, leading=10, textColor=MUTED,
        ),
        "table_text": ParagraphStyle(
            "StyleTableText", parent=base["BodyText"], fontName="Helvetica",
            fontSize=6.8, leading=8.5, alignment=TA_LEFT, textColor=colors.HexColor("#1F2937"),
        ),
        "table_center": ParagraphStyle(
            "StyleTableCenter", parent=base["BodyText"], fontName="Helvetica",
            fontSize=6.8, leading=8.5, alignment=TA_CENTER, textColor=colors.HexColor("#1F2937"),
        ),
        "table_right": ParagraphStyle(
            "StyleTableRight", parent=base["BodyText"], fontName="Helvetica",
            fontSize=6.8, leading=8.5, alignment=TA_RIGHT, textColor=colors.HexColor("#1F2937"),
        ),
        "table_header_left": ParagraphStyle(
            "StyleTableHeaderLeft", parent=base["BodyText"], fontName="Helvetica-Bold",
            fontSize=6.8, leading=8.5, alignment=TA_LEFT, textColor=colors.white,
        ),
        "table_header_center": ParagraphStyle(
            "StyleTableHeaderCenter", parent=base["BodyText"], fontName="Helvetica-Bold",
            fontSize=6.8, leading=8.5, alignment=TA_CENTER, textColor=colors.white,
        ),
        "table_header_right": ParagraphStyle(
            "StyleTableHeaderRight", parent=base["BodyText"], fontName="Helvetica-Bold",
            fontSize=6.8, leading=8.5, alignment=TA_RIGHT, textColor=colors.white,
        ),
        **{
            f"primary_{key}": ParagraphStyle(
                f"StylePrimary{key}", parent=base["BodyText"], fontName="Helvetica-Bold",
                fontSize=6.8, leading=8.5, alignment=TA_CENTER, textColor=colors.HexColor(color),
            )
            for key, color in STYLE_COLORS.items()
            if key != "Unclassified"
        },
    }


def _cell(value, style):
    return Paragraph(escape(str(value)), style)


def _styled_table(data, col_widths, alignments, font_size=7.5, repeat_rows=1, extra_commands=None):
    table = Table(data, colWidths=col_widths, repeatRows=repeat_rows)
    commands = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), font_size),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    for col_idx, alignment in alignments.items():
        commands.append(("ALIGN", (col_idx, 0), (col_idx, -1), alignment))
    if extra_commands:
        commands.extend(extra_commands)
    table.setStyle(TableStyle(commands))
    return table


def _style_bar(score, style_key):
    filled = max(1, min(10, round(score / 10))) if pd.notna(score) else 0
    cells = [["" for _ in range(10)]]
    table = Table(cells, colWidths=[8] * 10, rowHeights=[6])
    commands = [
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#E5E7EB")),
        ("BOX", (0, 0), (-1, -1), 0.2, colors.white),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.white),
    ]
    if filled:
        commands.append(("BACKGROUND", (0, 0), (filled - 1, 0), colors.HexColor(STYLE_COLORS[style_key])))
    table.setStyle(TableStyle(commands))
    return table


def build_style_story(analysis, doc_width, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    styles = _styles()

    config = analysis["config"]
    style_labels = {key: config["styles"][key]["label"] for key in analysis["style_keys"]}
    holdings = analysis["holdings"]
    style_mix = analysis["style_mix"].copy()
    style_mix["style_label"] = style_mix["primary_style"].map(
        lambda key: style_labels.get(key, "Unclassified")
    )

    as_of = analysis["as_of_date"]
    as_of_text = as_of.strftime("%d %b %Y") if as_of is not None else "N/A"

    story = [
        Paragraph("Stock Style Classification", styles["title"]),
        Paragraph(
            "Every holding is scored against Growth, Value, Momentum and Quality factors using "
            "percentile ranks against the full listed market universe, following "
            "Stock_Style_Rating_and_Scoring_Methodology_v1.docx. A style only becomes a holding's "
            "Primary or Secondary Style if it clears that style's minimum-metrics-passed rule. "
            "Volatility and Liquidity risk are reported separately in the Risk-O-Meter.",
            styles["small"],
        ),
        Paragraph(
            f"Fundamental data: latest Accord company filings. Price/momentum data as of {as_of_text}.",
            styles["small"],
        ),
        Spacer(1, 10),
    ]

    story.append(Paragraph("Overall Portfolio Style Profile", styles["section"]))
    story.append(Paragraph(
        "How much of each style the portfolio exhibits overall &mdash; the portfolio-weighted average "
        "score per style across every holding (regardless of which style each stock individually won). "
        "Coverage is the share of portfolio value with usable data for that style.",
        styles["small"],
    ))
    story.append(Spacer(1, 6))

    profile = analysis["portfolio_style_profile"].copy()
    profile_rows = [[
        _cell("Style", styles["table_header_left"]),
        _cell("Score", styles["table_header_right"]),
        _cell("Profile", styles["table_header_center"]),
        _cell("Coverage", styles["table_header_right"]),
    ]]
    for _, row in profile.iterrows():
        score_text = f"{row['weighted_score']:.1f}" if pd.notna(row["weighted_score"]) else "N/A"
        profile_rows.append([
            _cell(row["label"], styles[f"primary_{row['style']}"]),
            _cell(score_text, styles["table_right"]),
            _style_bar(row["weighted_score"], row["style"]),
            _cell(f"{row['coverage_percent']:.1f}%", styles["table_right"]),
        ])
    story.append(_styled_table(
        profile_rows, [130, 60, 90, 80], {0: "LEFT", 1: "RIGHT", 2: "CENTER", 3: "RIGHT"},
    ))
    story.append(Spacer(1, 14))

    donut_path = output_dir / "style_mix_donut.png"
    create_donut_chart(
        style_mix, "style_label", "allocation_percent",
        "Portfolio Style Mix", donut_path.name, "Primary Style\nAllocation",
    )
    story.append(Paragraph("Portfolio Style Mix", styles["section"]))
    story.append(Image(str(donut_path), width=6.4 * 72, height=4.6 * 72))
    story.append(Spacer(1, 6))

    mix_rows = [[
        _cell("Style", styles["table_header_left"]),
        _cell("Number of Holdings", styles["table_header_right"]),
        _cell("Portfolio Weight %", styles["table_header_right"]),
    ]]
    for _, row in style_mix.iterrows():
        mix_rows.append([
            _cell(row["style_label"], styles["table_text"]),
            _cell(int(row["holdings_count"]), styles["table_right"]),
            _cell(f"{row['allocation_percent']:.2f}%", styles["table_right"]),
        ])
    story.append(_styled_table(
        mix_rows, [doc_width - 240, 120, 120], {0: "LEFT", 1: "RIGHT", 2: "RIGHT"},
    ))
    story.append(PageBreak())

    story.append(Paragraph("Holding-wise Style Classification", styles["section"]))
    story.append(Paragraph(
        "Primary/Secondary Style is the highest/second-highest eligible style score. "
        "Rating reflects the Primary Style score against the Final Rating Bands.",
        styles["small"],
    ))
    story.append(Spacer(1, 8))

    detail_rows = [[
        _cell("Company", styles["table_header_left"]),
        _cell("ISIN", styles["table_header_center"]),
        _cell("Wt %", styles["table_header_right"]),
        _cell("Cap", styles["table_header_center"]),
        _cell("Primary Style", styles["table_header_center"]),
        _cell("Score", styles["table_header_right"]),
        _cell("Secondary Style", styles["table_header_center"]),
        _cell("Rating", styles["table_header_center"]),
    ]]
    for _, row in holdings.iterrows():
        primary_label = style_labels.get(row["primary_style"], "Unclassified")
        secondary_label = style_labels.get(row["secondary_style"], "-")
        score_text = f"{row['primary_score']:.1f}" if row["primary_score"] == row["primary_score"] else "N/A"
        detail_rows.append([
            _cell(row["company_name"], styles["table_text"]),
            _cell(row["isin"], styles["table_center"]),
            _cell(f"{row['weight'] * 100:.2f}%", styles["table_right"]),
            _cell(row["market_cap_size"], styles["table_center"]),
            _cell(primary_label, styles["table_center"]),
            _cell(score_text, styles["table_right"]),
            _cell(secondary_label, styles["table_center"]),
            _cell(row["rating"], styles["table_center"]),
        ])

    col_widths = [110, 68, 38, 42, 66, 34, 66, 62]
    story.append(_styled_table(
        detail_rows, col_widths,
        {0: "LEFT", 1: "CENTER", 2: "RIGHT", 3: "CENTER", 4: "CENTER", 5: "RIGHT", 6: "CENTER", 7: "CENTER"},
    ))
    story.append(PageBreak())

    story.append(Paragraph("Style Score Matrix", styles["section"]))
    story.append(Paragraph(
        f"Every holding's score (0-100) against all {len(analysis['style_keys'])} styles. A plain "
        "score means the stock is eligible for that style (cleared its minimum-metrics-passed "
        "rule). A score in parentheses means it was scored on complete data but did not qualify. "
        "A score marked with * means it is ineligible only because too few metrics could be "
        "computed for it -- most commonly a recently listed company that doesn't yet have the "
        "full history a style like Growth requires -- and should not be read as a genuine "
        "failing score. The highlighted cell is each holding's Primary Style.",
        styles["small"],
    ))
    story.append(Spacer(1, 8))

    matrix_header = [_cell("Company", styles["table_header_left"])] + [
        _cell(style_labels[key], styles["table_header_center"]) for key in analysis["style_keys"]
    ]
    matrix_rows = [matrix_header]
    highlight_commands = []
    for display_row, (_, row) in enumerate(holdings.iterrows(), start=1):
        cells = [_cell(row["company_name"], styles["table_text"])]
        for col_idx, key in enumerate(analysis["style_keys"], start=1):
            score = row[f"{key}_score"]
            eligible = row[f"{key}_eligible"]
            available_count = row[f"{key}_available_count"]
            total_metrics = row[f"{key}_total_metrics"]
            is_primary = key == row["primary_style"]

            if pd.isna(score):
                text = "N/A"
            elif eligible:
                text = f"{score:.1f}"
            elif available_count < total_metrics:
                text = f"{score:.1f}*"
            else:
                text = f"({score:.1f})"

            cell_style = styles[f"primary_{key}"] if is_primary else styles["table_center"]
            cells.append(_cell(text, cell_style))

            if is_primary:
                highlight_commands.append((
                    "BACKGROUND", (col_idx, display_row), (col_idx, display_row),
                    colors.HexColor(STYLE_HIGHLIGHT_COLORS[key]),
                ))
        matrix_rows.append(cells)

    style_count = len(analysis["style_keys"])
    matrix_col_widths = [doc_width - 60 * style_count] + [60] * style_count
    story.append(_styled_table(
        matrix_rows, matrix_col_widths,
        {0: "LEFT", **{i: "CENTER" for i in range(1, style_count + 1)}},
        extra_commands=highlight_commands,
    ))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "N/A means no metric for that style could be computed at all for that stock (e.g. no "
        "price history at all). * means the style couldn't be fully evaluated -- not enough "
        "metrics had data -- rather than the stock genuinely underperforming.",
        styles["small"],
    ))
    story.append(PageBreak())

    story.append(Paragraph("Style Definitions", styles["section"]))
    definition_rows = [[
        _cell("Style", styles["table_header_left"]),
        _cell("Definition", styles["table_header_left"]),
        _cell("Eligibility Rule", styles["table_header_left"]),
    ]]
    for key in analysis["style_keys"]:
        style_cfg = config["styles"][key]
        total_metrics = len(style_cfg["metrics"])
        definition_rows.append([
            _cell(style_cfg["label"], styles["table_text"]),
            _cell(style_cfg["definition"], styles["table_text"]),
            _cell(f"Pass at least {style_cfg['min_pass']} of {total_metrics} metrics", styles["table_text"]),
        ])
    story.append(_styled_table(
        definition_rows, [90, doc_width - 90 - 160, 160],
        {0: "LEFT", 1: "LEFT", 2: "LEFT"}, repeat_rows=1,
    ))

    story.append(Spacer(1, 8))
    if "growth" in analysis["style_keys"]:
        story.append(Paragraph(
            "Growth requires a full 5-year history for every metric. A company listed less than "
            "5 years ago will show N/A for Growth in the Style Score Matrix -- this reflects "
            "insufficient listing history, not a failing Growth score.",
            styles["small"],
        ))
    story.append(Paragraph(
        "Methodology note: thresholds and weights are configurable in style_config.json. "
        "This classification is an analytical indicator, not investment advice.",
        styles["small"],
    ))

    return story
