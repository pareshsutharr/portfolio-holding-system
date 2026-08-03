"""Generate the standalone Portfolio Risk-O-Meter Scoring Methodology document.

Unlike scripts/generate_risk_calculation_doc.py (which recomputes and explains
one portfolio's actual numbers from the database), this script documents the
methodology itself: modules, formulas, thresholds and rating bands, sourced
from riskometer.py and riskometer_config.json. It requires no database or
holdings file.
"""

from __future__ import annotations

import json
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.shared import Pt

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "Riskometer_Scoring_Methodology_v1.docx"


def _add_table(document: Document, headers: list[str], rows: list[list[str]]) -> None:
    table = document.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for index, header in enumerate(headers):
        cell = table.rows[0].cells[index]
        cell.text = ""
        run = cell.paragraphs[0].add_run(header)
        run.bold = True
    for row in rows:
        cells = table.add_row().cells
        for index, value in enumerate(row):
            cells[index].text = str(value)


def _module_section(
    document: Document,
    title: str,
    definition: str,
    formula_lines: list[str],
    table_headers: list[str],
    table_rows: list[list[str]],
    scoring: str,
    notes: list[str] | None = None,
) -> None:
    document.add_heading(title, level=2)
    document.add_paragraph(f"Definition: {definition}")
    for line in formula_lines:
        document.add_paragraph(line)
    _add_table(document, table_headers, table_rows)
    document.add_paragraph(f"Scoring: {scoring}")
    for note in notes or []:
        document.add_paragraph(note, style="List Bullet")


def generate() -> Path:
    config = json.loads((ROOT / "riskometer_config.json").read_text(encoding="utf-8"))
    weights = config["module_weights"]
    mc = config["market_cap_scores"]

    document = Document()
    document.add_heading("Portfolio Risk-O-Meter Scoring Methodology (Version 1)", level=1)
    document.add_paragraph(
        "This document defines the modules, formulas, thresholds and rating bands "
        "used to compute the Portfolio Risk-O-Meter. Every underlying metric is "
        "normalized to a 0-100 risk score, where a higher score means higher "
        "measured risk. The overall Risk-O-Meter score is the weighted average of "
        "seven risk modules, each covering a distinct dimension of portfolio risk."
    )

    document.add_heading("1. Module Weights", level=1)
    document.add_paragraph(
        "The overall score is: Sum(Module Score x Module Weight), across all seven "
        "modules. All module scores and weights are on the same 0-100 / percentage "
        "basis, so the overall score is also 0-100."
    )
    _add_table(
        document,
        ["Module", "Weight"],
        [
            ["Concentration Risk", f"{weights['concentration'] * 100:.0f}%"],
            ["Sector Risk", f"{weights['sector'] * 100:.0f}%"],
            ["Market Cap Risk", f"{weights['market_cap'] * 100:.0f}%"],
            ["Fundamental Quality Risk", f"{weights['quality'] * 100:.0f}%"],
            ["Liquidity Risk", f"{weights['liquidity'] * 100:.0f}%"],
            ["Volatility Risk", f"{weights['volatility'] * 100:.0f}%"],
            ["Beta Risk", f"{weights['beta'] * 100:.0f}%"],
            ["Total", "100%"],
        ],
    )

    document.add_heading("2. Risk Rating Bands", level=1)
    document.add_paragraph(
        "The overall 0-100 score is mapped to a rating band. Bands are cumulative "
        "upper limits: a score is assigned to the first band whose maximum it does "
        "not exceed."
    )
    band_rows = []
    previous = 0
    for band in config["risk_levels"]:
        band_rows.append([f"{previous}-{band['max']}", band["label"]])
        previous = band["max"]
    _add_table(document, ["Score Range", "Rating"], band_rows)

    document.add_heading("3. Normalization Methods", level=1)
    document.add_paragraph(
        "Three normalization methods convert raw metrics onto the common 0-100 "
        "risk scale. Every module below states which method applies to each of "
        "its metrics."
    )
    _add_table(
        document,
        ["Method", "Used When", "Formula"],
        [
            [
                "Direct-Bad",
                "Higher raw value = higher risk (e.g. concentration %, Debt/Equity, volatility)",
                "Risk = 100 x min(max(Value, 0), High) / High",
            ],
            [
                "Inverse-Good",
                "Higher raw value = lower risk (e.g. ROE, ROCE, Interest Cover, sector count)",
                "Risk = 100 x (1 - min(max(Value, 0), Good) / Good)",
            ],
            [
                "Log-Inverse",
                "Higher raw value = lower risk, over a wide multi-order-of-magnitude "
                "range (traded volume, turnover)",
                "Risk = 100 if Value <= Low; 0 if Value >= High; otherwise "
                "100 x (1 - (ln(Value) - ln(Low)) / (ln(High) - ln(Low)))",
            ],
            [
                "Linear Scale",
                "Beta, which can meaningfully be below the low bound or above the "
                "high bound",
                "Risk = clip(100 x (Beta - Low) / (High - Low), 0, 100)",
            ],
        ],
    )
    document.add_paragraph(
        "All results are clipped to the 0-100 range and rounded to two decimals. "
        "All thresholds (\"High\", \"Good\", \"Low\") are configured in "
        "riskometer_config.json and can be revised without code changes."
    )

    document.add_heading("4. Risk Modules", level=1)

    c = config["concentration"]
    _module_section(
        document,
        "4.1 Concentration Risk",
        "Risk arising from a small number of holdings dominating the portfolio.",
        [
            "Metrics: Largest Holding %, Top 3 Holdings %, Top 5 Holdings %, and "
            "Holding HHI (sum of squared portfolio weights).",
        ],
        ["Metric", "Method", "Threshold (High)"],
        [
            ["Largest Holding %", "Direct-Bad", f"{c['largest_holding_high']}%"],
            ["Top 3 Holdings %", "Direct-Bad", f"{c['top3_high']}%"],
            ["Top 5 Holdings %", "Direct-Bad", f"{c['top5_high']}%"],
            ["Holding HHI", "Direct-Bad", f"{c['hhi_high']}"],
        ],
        "Concentration Risk = simple average of the four normalized risks.",
    )

    s = config["sector"]
    _module_section(
        document,
        "4.2 Sector Risk",
        "Risk arising from overexposure to, or under-diversification across, NSE "
        "sectors.",
        [
            "Metrics: Largest Sector %, Sector HHI (sum of squared sector "
            "weights), and Sector Count.",
        ],
        ["Metric", "Method", "Threshold"],
        [
            ["Largest Sector %", "Direct-Bad", f"High = {s['largest_sector_high']}%"],
            ["Sector HHI", "Direct-Bad", f"High = {s['sector_hhi_high']}"],
            [
                "Sector Count",
                "Inverse-Good",
                f"Good (well-diversified) = {s['well_diversified_sector_count']} sectors",
            ],
        ],
        "Sector Risk = simple average of the three normalized risks.",
    )

    _module_section(
        document,
        "4.3 Market Cap Risk",
        "Risk arising from allocation to smaller, less-established market "
        "capitalization categories, per the SEBI market-cap classification.",
        [
            "Method: portfolio-weighted sum of a configured risk score per SEBI "
            "market-cap category.",
        ],
        ["Category", "Configured Risk Score"],
        [[category, str(score)] for category, score in mc.items()],
        "Market Cap Risk = Sum(Portfolio weight in category x Configured category "
        "score), across all categories held.",
    )

    q = config["quality"]
    _module_section(
        document,
        "4.4 Fundamental Quality Risk",
        "Risk arising from weak profitability, capital efficiency or balance-sheet "
        "leverage at the underlying companies.",
        [
            "Metrics: ROE, ROCE, Debt/Equity, and Interest Coverage (most recent "
            "financial year available per company).",
        ],
        ["Metric", "Method", "Threshold"],
        [
            ["ROE", "Inverse-Good", f"Good = {q['roe_good']}%"],
            ["ROCE", "Inverse-Good", f"Good = {q['roce_good']}%"],
            ["Debt/Equity", "Direct-Bad", f"High = {q['debt_equity_high']}"],
            ["Interest Coverage", "Inverse-Good", f"Good = {q['interest_cover_good']}x"],
        ],
        "Stock Quality Risk = average of the applicable component risks. "
        "Fundamental Quality Risk = weighted average of Stock Quality Risk across "
        "all eligible holdings for which every required metric is available, "
        "weighted by portfolio value.",
        [
            "ETFs are excluded entirely from Fundamental Quality scoring (fundamentals "
            "are Not Applicable); they are still scored in every other module.",
            "Banks, NBFCs, insurers and other financial-service companies are scored "
            "on ROE, ROCE and Debt/Equity only — Interest Coverage is marked Not "
            "Applicable for these companies.",
            "Coverage (the % of eligible portfolio value with complete, calculable "
            "data) is disclosed alongside the module score. If no eligible holding has "
            "complete data, the module defaults to a risk score of 100 (maximum risk) "
            "as a conservative fallback rather than silently excluding the module.",
        ],
    )

    hist = config["history"]
    _module_section(
        document,
        "4.5 Liquidity Risk",
        "Risk that a holding cannot be exited without significant market impact, "
        "based on recent trading activity.",
        [
            f"Metrics: average daily traded Volume and average daily Turnover, over "
            f"the most recent {hist['liquidity_days']} trading days.",
            "Thresholds are cap-tiered: each stock is judged against the Low/High "
            "band for its own SEBI market-cap category, not one universal band. "
            "This avoids penalizing small-cap stocks for trading less than "
            "large-caps naturally do, and vice versa.",
        ],
        ["Cap Category", "Volume Low-High ('000 shares)", "Turnover Low-High (Rs. Crore)"],
        [
            ["Large Cap", "50 - 2000", "5 - 200"],
            ["Mid Cap", "20 - 800", "2 - 80"],
            ["Small Cap", "5 - 300", "0.5 - 30"],
        ],
        "Stock Liquidity Risk = average of Volume Risk and Turnover Risk "
        "(Log-Inverse method, using the stock's own cap-tier Low/High band). "
        "Liquidity Risk = weighted average of Stock Liquidity Risk across holdings "
        "with available trading data, weighted by portfolio value.",
        [
            "Coverage (% of portfolio value with usable trading data) is disclosed "
            "alongside the module score; the module defaults to 100 (maximum risk) "
            "if no holding has usable data.",
            "A holding with an Unknown market-cap category (unmapped ISIN) falls "
            "back to the Small Cap band, the most conservative (hardest-to-clear) "
            "tier.",
        ],
    )

    vol = config["volatility"]
    _module_section(
        document,
        "4.6 Volatility Risk",
        "Risk arising from the magnitude and severity of historical price "
        "fluctuations.",
        [
            f"Metrics: Annualized Volatility, Maximum Drawdown and Downside "
            f"Volatility, computed from up to {hist['trading_days']} trading days of "
            f"daily returns (minimum {hist['minimum_return_observations']} "
            "observations required).",
            "Annualized Volatility = daily return standard deviation x sqrt(252). "
            "Maximum Drawdown = largest peak-to-trough decline in cumulative "
            "wealth. Downside Volatility = standard deviation of negative daily "
            "returns x sqrt(252).",
        ],
        ["Metric", "Method", "Threshold (High)"],
        [
            ["Annualized Volatility", "Direct-Bad", f"{vol['annualized_volatility_high'] * 100:.0f}%"],
            ["Maximum Drawdown", "Direct-Bad", f"{vol['maximum_drawdown_high'] * 100:.0f}%"],
            ["Downside Volatility", "Direct-Bad", f"{vol['downside_volatility_high'] * 100:.0f}%"],
        ],
        "Stock Volatility Risk = average of the three normalized risks. "
        "Volatility Risk = weighted average of Stock Volatility Risk across "
        "holdings with sufficient return history, weighted by portfolio value.",
        [
            "Coverage is disclosed alongside the module score; the module defaults "
            "to 100 (maximum risk) if no holding has sufficient return history.",
        ],
    )

    beta_cfg = config["beta"]
    _module_section(
        document,
        "4.7 Beta Risk",
        "Risk arising from a stock's sensitivity to broad market movements, "
        "relative to a market-cap-appropriate benchmark index.",
        [
            "Beta = Covariance(stock daily returns, benchmark daily returns) / "
            "Variance(benchmark daily returns), computed on overlapping trading "
            f"dates (minimum {hist['minimum_return_observations']} observations "
            "required).",
            "The benchmark is chosen by the stock's own SEBI market-cap category, "
            "not NIFTY 50 for every stock: Large Cap uses Nifty 50, Mid Cap uses "
            "Nifty Midcap 150, and Small Cap uses Nifty 500. This avoids "
            "comparing a small-cap stock's sensitivity against a large-cap-only "
            "index, which understates or distorts its true Beta.",
        ],
        ["Cap Category", "Benchmark Used"],
        [
            ["Large Cap", "Nifty 50"],
            ["Mid Cap", "Nifty Midcap 150"],
            ["Small Cap", "Nifty 500"],
        ],
        "Stock Beta Risk = clip(100 x (Beta - Low) / (High - Low), 0, 100), with "
        f"Low = {beta_cfg['low']} (0 risk) and High = {beta_cfg['high']} (100 risk), "
        "applied identically regardless of which benchmark the Beta itself was "
        "computed against. Beta Risk = weighted average of Stock Beta Risk across "
        "holdings with sufficient overlapping return history, weighted by "
        "portfolio value.",
        [
            "Coverage is disclosed alongside the module score; the module defaults "
            "to 100 (maximum risk) if no holding has sufficient overlapping history "
            "with its benchmark.",
        ],
    )

    document.add_heading("5. Overall Score and Worked Aggregation", level=1)
    document.add_paragraph(
        "Overall Risk-O-Meter Score = Sum(Module Score x Module Weight), clipped "
        "to 0-100 and rounded to two decimals. The Overall Rating is then read "
        "from the bands in Section 2."
    )
    document.add_paragraph(
        "Example: if Concentration = 35, Sector = 40, Market Cap = 30, Quality = "
        "25, Liquidity = 20, Volatility = 45 and Beta = 50, then Overall = "
        "35(0.15) + 40(0.15) + 30(0.10) + 25(0.15) + 20(0.10) + 45(0.20) + 50(0.15) "
        "= 36.50, which falls in the Low band (20-40) per Section 2."
    )

    document.add_heading("6. Configurability", level=1)
    document.add_paragraph(
        "All module weights, thresholds, rating bands and lookback windows used "
        "in this methodology are defined in riskometer_config.json and can be "
        "revised centrally without changing the scoring code in riskometer.py. "
        "A fully transparent, stock-by-stock recalculation for any specific "
        "portfolio is produced separately by "
        "scripts/generate_risk_calculation_doc.py."
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    document.save(OUTPUT)
    return OUTPUT


if __name__ == "__main__":
    print(generate())
