import json
from pathlib import Path

import pandas as pd

from riskometer import Riskometer


def _riskometer() -> Riskometer:
    meter = Riskometer.__new__(Riskometer)
    meter.config = json.loads(
        Path("riskometer_config.json").read_text(encoding="utf-8")
    )
    return meter


def test_quality_excludes_etfs_and_waives_financial_interest_cover() -> None:
    portfolio = pd.DataFrame(
        [
            {
                "isin": "BANK",
                "security_name": "Example Bank Ltd",
                "weight": 0.60,
                "ace_sector": "Bank",
                "nse_sector": "Financial Services",
            },
            {
                "isin": "INDUSTRIAL",
                "security_name": "Example Engineering Ltd",
                "weight": 0.30,
                "ace_sector": "Capital Goods",
                "nse_sector": "Capital Goods",
            },
            {
                "isin": "ETF",
                "security_name": "Example Gold ETF",
                "weight": 0.10,
                "ace_sector": "ETF",
                "nse_sector": "ETF",
            },
        ]
    )
    fundamentals = pd.DataFrame(
        [
            {
                "isin": "BANK",
                "roe": 20,
                "roce": 20,
                "debt_equity": 0,
                "interest_cover": None,
            },
            {
                "isin": "INDUSTRIAL",
                "roe": 20,
                "roce": 20,
                "debt_equity": 0,
                "interest_cover": 8,
            },
        ]
    )

    result = _riskometer()._quality(portfolio, fundamentals)

    assert result.score == 0
    assert result.coverage == "100.0% of eligible company value"
    assert result.values["ETFs excluded"] == 1
    assert result.values["Financials with Interest Cover N/A"] == 1


def test_quality_does_not_score_incomplete_non_financial_company() -> None:
    portfolio = pd.DataFrame(
        [
            {
                "isin": "COMPLETE",
                "security_name": "Complete Ltd",
                "weight": 0.70,
                "ace_sector": "IT",
                "nse_sector": "Information Technology",
            },
            {
                "isin": "INCOMPLETE",
                "security_name": "Incomplete Ltd",
                "weight": 0.30,
                "ace_sector": "IT",
                "nse_sector": "Information Technology",
            },
        ]
    )
    fundamentals = pd.DataFrame(
        [
            {
                "isin": "COMPLETE",
                "roe": 20,
                "roce": 20,
                "debt_equity": 0,
                "interest_cover": 8,
            },
            {
                "isin": "INCOMPLETE",
                "roe": 20,
                "roce": 20,
                "debt_equity": 0,
                "interest_cover": None,
            },
        ]
    )

    result = _riskometer()._quality(portfolio, fundamentals)

    assert result.score == 0
    assert result.coverage == "70.0% of eligible company value"
