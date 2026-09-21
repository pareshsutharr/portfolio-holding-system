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
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from charts import create_donut_chart

NAVY = colors.HexColor("#0F172A")
ACCENT = colors.HexColor("#1D4ED8")
HEADING_RED = colors.HexColor("#123A63")
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
            fontSize=13, leading=16, textColor=colors.HexColor("#0E8290"), spaceAfter=6,
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

    left_width = doc_width * 0.35
    right_width = doc_width * 0.62

    story = [
        Paragraph(
            "STYLE ANALYSIS",
            ParagraphStyle("StyleKicker", parent=styles["small"], fontName="Helvetica-Bold", fontSize=7, textColor=colors.HexColor("#0E8290"), spaceAfter=2),
        ),
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
        Spacer(1, 4),
    ]

    # ----- Left column: portfolio style profile + style mix -----
    left_column = [
        Paragraph("Overall Portfolio Style Profile", styles["section"]),
        Paragraph(
            "Portfolio-weighted average score per style across every holding. Coverage is the "
            "share of value with usable data.",
            styles["small"],
        ),
        Spacer(1, 4),
    ]

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
    left_column.append(_styled_table(
        profile_rows,
        [left_width * 0.36, left_width * 0.16, left_width * 0.28, left_width * 0.20],
        {0: "LEFT", 1: "RIGHT", 2: "CENTER", 3: "RIGHT"},
        font_size=6.6,
        extra_commands=[
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ],
    ))
    left_column.append(Spacer(1, 6))

    donut_path = output_dir / "style_mix_donut.png"
    create_donut_chart(
        style_mix, "style_label", "allocation_percent",
        "Portfolio Style Mix", donut_path.name, "Primary Style\nAllocation",
    )
    mix_rows = [[
        _cell("Style", styles["table_header_left"]),
        _cell("Holdings", styles["table_header_right"]),
        _cell("Weight %", styles["table_header_right"]),
    ]]
    for _, row in style_mix.iterrows():
        mix_rows.append([
            _cell(row["style_label"], styles["table_text"]),
            _cell(int(row["holdings_count"]), styles["table_right"]),
            _cell(f"{row['allocation_percent']:.2f}%", styles["table_right"]),
        ])
    compact_mix_table = _styled_table(
        mix_rows,
        [left_width * 0.42, left_width * 0.28, left_width * 0.28],
        {0: "LEFT", 1: "RIGHT", 2: "RIGHT"},
        font_size=6.6,
        extra_commands=[
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ],
    )
    left_column.append(Paragraph("Portfolio Style Mix", styles["section"]))
    left_column.append(Image(str(donut_path), width=left_width * 0.58, height=left_width * 0.58 * 0.58))
    left_column.append(Spacer(1, 3))
    left_column.append(compact_mix_table)

    # ----- Right column: per-holding style score matrix -----
    right_column = [
        Paragraph("Style Score Matrix", styles["section"]),
        Paragraph(
            f"Every holding's score (0-100) against all {len(analysis['style_keys'])} styles. A plain "
            "score is eligible (cleared the minimum-metrics-passed rule); a score in parentheses was "
            "scored but didn't qualify; a score marked * is ineligible only because too few metrics "
            "could be computed (e.g. a recent listing), not a genuine failing score. The highlighted "
            "cell is each holding's Primary Style.",
            styles["small"],
        ),
        Spacer(1, 4),
    ]

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
    matrix_col_widths = [right_width - 46 * style_count] + [46] * style_count
    right_column.append(_styled_table(
        matrix_rows, matrix_col_widths,
        {0: "LEFT", **{i: "CENTER" for i in range(1, style_count + 1)}},
        font_size=6.2,
        extra_commands=highlight_commands + [
            ("TOPPADDING", (0, 0), (-1, -1), 2.0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.0),
        ],
    ))
    right_column.append(Spacer(1, 3))
    right_column.append(Paragraph(
        "N/A means no metric for that style could be computed at all for that stock. * means the "
        "style couldn't be fully evaluated -- not enough metrics had data -- rather than the stock "
        "genuinely underperforming. Methodology note: thresholds and weights are configurable in "
        "style_config.json. This classification is an analytical indicator, not investment advice.",
        styles["small"],
    ))

    columns = Table(
        [[left_column, right_column]],
        colWidths=[left_width, right_width],
        hAlign="LEFT",
    )
    columns.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (0, 0), 0),
        ("RIGHTPADDING", (0, 0), (0, 0), 14),
        ("LEFTPADDING", (1, 0), (1, 0), 14),
        ("RIGHTPADDING", (1, 0), (1, 0), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("LINEBEFORE", (1, 0), (1, 0), 0.5, BORDER),
    ]))
    story.append(columns)

    return [KeepTogether(story)]
