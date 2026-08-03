"""Generate Stock_Style_Rating_and_Scoring_Methodology_v1.docx.

Documentation aid only -- does not touch stock_style.py, stock_style_scoring.py,
stock_style_universe.py, stock_style_market.py, or style_config.json.

Updates from the original version:
  - Low Volatility and Liquidity sections removed entirely -- both are
    already calculated at the portfolio level in the Risk-O-Meter, so they
    are not duplicated here (matches the change already made to
    Stock_Style_Classification_Methodology_v1.docx).
  - Value's P/E, P/B, EV/EBITDA and Dividend Yield minimum requirements are
    now stated against the stock's NSE sectoral index, not "market median".
  - Final Classification paragraph updated to drop Low Volatility and
    Liquidity from the list of style scores every stock receives.
"""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "Stock_Style_Rating_and_Scoring_Methodology_v1.docx"

FILLED_STAR = "★"
EMPTY_STAR = "☆"


def _add_table(document: Document, headers: list[str], rows: list[list[str]]) -> None:
    table = document.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for index, header in enumerate(headers):
        table.rows[0].cells[index].text = header
    for row in rows:
        cells = table.add_row().cells
        for index, value in enumerate(row):
            cells[index].text = str(value)


def _style_section(document: Document, name: str, definition: str, eligibility: str, metrics: list[list[str]]) -> None:
    document.add_heading(name, level=2)
    document.add_paragraph(f"Definition: {definition}")
    document.add_paragraph(f"Eligibility Rule: {eligibility}")
    document.add_paragraph(
        "Scoring: Convert each eligible metric to a 0-100 score. Style "
        "Score = Weighted average of metric scores."
    )
    _add_table(document, ["Metric", "Minimum Requirement", "Weight"], metrics)


def generate() -> Path:
    document = Document()
    document.add_heading("Stock Style Rating & Scoring Methodology (Version 1)", level=1)
    document.add_paragraph(
        "This document defines the minimum eligibility criteria, scoring "
        "methodology and rating framework for classifying stocks."
    )

    _style_section(
        document, "Growth",
        "A company showing sustained earnings and business growth.",
        "Pass at least 4 of 5 metrics.",
        [
            ["Revenue Growth (5Y CAGR)", ">=10%", "20%"],
            ["PAT Growth (5Y CAGR)", ">=10%", "20%"],
            ["EPS Growth (5Y CAGR)", ">=10%", "20%"],
            ["ROE", ">=15%", "20%"],
            ["ROCE", ">=15%", "20%"],
        ],
    )
    document.add_paragraph(
        "All five Growth metrics require a full 5-year history. A company listed less than 5 "
        "years ago will have no computable Growth metrics and is reported as Not Applicable "
        "(insufficient listing history) for Growth -- this is distinct from, and should not be "
        "confused with, a stock that is scored on complete data but genuinely underperforms."
    )

    _style_section(
        document, "Value",
        "A fundamentally attractive company trading at reasonable valuation.",
        "Pass at least 3 of 4 metrics.",
        [
            ["P/E", "Lower than NSE sectoral index P/E", "25%"],
            ["P/B", "Lower than NSE sectoral index P/B", "25%"],
            ["EV/EBITDA", "Lower than NSE sectoral index EV/EBITDA", "25%"],
            ["Dividend Yield", "Higher than NSE sectoral index Dividend Yield", "25%"],
        ],
    )
    document.add_paragraph(
        "Note: minimum requirements are benchmarked against the stock's own "
        "NSE sectoral index rather than the whole market, so naturally "
        "high-multiple sectors (e.g. IT) and naturally low-multiple sectors "
        "(e.g. PSUs, cyclicals) are compared against fair, sector-relative "
        "expectations instead of one universal bar."
    )

    _style_section(
        document, "Momentum",
        "A stock exhibiting sustained positive price trend.",
        "Pass at least 3 of 4 metrics.",
        [
            ["6M Return", "Positive", "25%"],
            ["12M Return", "Positive", "25%"],
            ["Relative Strength vs Nifty", ">1", "25%"],
            ["Price > 200 DMA", "Yes", "25%"],
        ],
    )
    document.add_paragraph(
        "Relative Strength = (1 + 12M Stock Return) / (1 + 12M Nifty "
        "Return); a ratio above 1 means the stock outperformed Nifty over "
        "the trailing 12 months."
    )

    _style_section(
        document, "Quality",
        "A financially strong business with efficient capital allocation.",
        "Pass at least 3 of 4 metrics.",
        [
            ["ROE", ">=15%", "25%"],
            ["ROCE", ">=15%", "25%"],
            ["Debt/Equity", "<=0.50", "25%"],
            ["Interest Coverage", ">=5", "25%"],
        ],
    )

    _style_section(
        document, "Size",
        "Classification by market capitalization.",
        "Classification only.",
        [
            ["Large Cap", "Top 100", "-"],
            ["Mid Cap", "Next 150", "-"],
            ["Small Cap", "Remaining", "-"],
        ],
    )

    document.add_heading("Final Rating Bands", level=2)
    _add_table(
        document,
        ["Score", "Rating", "Interpretation"],
        [
            ["90-100", FILLED_STAR * 5, "Exceptional"],
            ["80-89", FILLED_STAR * 4 + EMPTY_STAR, "Very Strong"],
            ["70-79", FILLED_STAR * 4, "Strong"],
            ["60-69", FILLED_STAR * 3 + EMPTY_STAR, "Moderate"],
            ["50-59", FILLED_STAR * 3, "Average"],
            ["40-49", FILLED_STAR * 2 + EMPTY_STAR, "Weak"],
            ["<40", FILLED_STAR, "Very Weak"],
        ],
    )

    document.add_heading("Final Classification", level=2)
    document.add_paragraph(
        "Every stock receives Growth, Value, Momentum, Quality and Size "
        "scores. Primary Style is the highest score; Secondary Style is "
        "the second-highest score. Volatility and Liquidity risk are "
        "reported separately at the portfolio level in the Risk-O-Meter "
        "and do not contribute to Primary/Secondary Style."
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    document.save(OUTPUT)
    return OUTPUT


if __name__ == "__main__":
    print(generate())
