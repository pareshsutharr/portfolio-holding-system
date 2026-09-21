"""Reusable orchestration for CLI and web portfolio analyses."""

from __future__ import annotations

import json
import math
import warnings
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

warnings.filterwarnings(
    "ignore",
    message="Workbook contains no default style, apply openpyxl's default",
    category=UserWarning,
    module=r"openpyxl\.styles\.stylesheet",
)

from benchmark_analysis import analyze_all_benchmarks
from benchmark_charts import generate_benchmark_charts
from benchmark_reader import load_all_benchmarks
from charts import generate_all_charts
from config import STYLE_CONFIG_FILE
from gemini_mapper import get_column_mapping
from header_detection import detect_header
from holdings_parser import parse_holdings
from market_cap import add_market_cap
from market_etl.config import Settings
from market_etl.database import build_engine
from pdf_holdings_parser import parse_pdf_portfolio
from pdf_reports import PortfolioPDF
from portfolio_analysis import analyze_portfolio
from portfolio_returns import analyze_disparity, analyze_portfolio_returns
from riskometer import Riskometer
from sector_industry import add_sector_industry
from sector_mapping import apply_sector_mapping
from stock_style import StockStyleClassifier
from yahoo_prices import add_yahoo_current_prices


def json_safe(value: Any) -> Any:
    """Convert pandas/numpy/domain objects to strict JSON-compatible values."""
    if is_dataclass(value):
        return json_safe(asdict(value))
    if isinstance(value, pd.DataFrame):
        return json_safe(value.to_dict(orient="records"))
    if isinstance(value, pd.Series):
        return json_safe(value.to_dict())
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    return value


class PortfolioAnalysisService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.from_env()
        self.engine = build_engine(self.settings.database_url)

    def _parse_holdings_file(self, holdings_file: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
        """Route to the PDF or Excel holdings parser by file extension, returning
        the standardized holdings DataFrame plus source-specific metadata."""
        if holdings_file.suffix.lower() == ".pdf":
            parsed, unresolved_names = parse_pdf_portfolio(holdings_file)
            return parsed, {"source": "pdf", "unresolved_names": unresolved_names}

        detected = detect_header(holdings_file)
        mapping = get_column_mapping(detected["headers"])
        parsed = parse_holdings(
            detected["dataframe"],
            detected["header_row"],
            detected["headers"],
            mapping,
        )
        return parsed, {
            "source": "excel",
            "header_row": detected["header_row"],
            "headers": detected["headers"],
            "mapping": mapping,
        }

    def preview(self, holdings_file: Path) -> dict[str, Any]:
        parsed, meta = self._parse_holdings_file(holdings_file)
        priced = add_yahoo_current_prices(add_market_cap(parsed))
        payload = {
            "holdings": priced.head(12),
            "holding_count": len(priced),
            "portfolio_value": priced["value"].sum(),
        }
        if meta["source"] == "excel":
            payload.update(header_row=meta["header_row"], headers=meta["headers"], mapping=meta["mapping"])
        else:
            payload["unresolved_names"] = meta["unresolved_names"]
        return json_safe(payload)

    def analyze(self, holdings_file: Path, output_pdf: Path, report_options: dict | None = None) -> dict[str, Any]:
        portfolio, meta = self._parse_holdings_file(holdings_file)
        if portfolio.empty:
            raise ValueError(
                "No valid holdings could be parsed from this file. Check that the "
                "ISIN, Quantity, and Closing Value columns contain valid values."
            )
        portfolio = add_sector_industry(portfolio)
        portfolio = apply_sector_mapping(portfolio)
        portfolio = add_market_cap(portfolio)
        portfolio = add_yahoo_current_prices(portfolio)
        analysis = analyze_portfolio(portfolio)
        risk = Riskometer(self.engine, Path("riskometer_config.json")).analyze(portfolio)
        style = StockStyleClassifier(Path(STYLE_CONFIG_FILE)).analyze(portfolio)
        returns = analyze_portfolio_returns(portfolio)
        disparity = analyze_disparity(portfolio)
        analysis = analyze_all_benchmarks(analysis, load_all_benchmarks())
        chart_paths = generate_all_charts(analysis)
        chart_paths.update(generate_benchmark_charts(analysis))
        output_pdf.parent.mkdir(parents=True, exist_ok=True)
        PortfolioPDF(
            analysis=analysis,
            chart_paths=chart_paths,
            risk_analysis=risk,
            style_analysis=style,
            disparity_analysis=disparity,
            output_path=output_pdf,
            report_options=report_options,
        ).generate()
        return json_safe(
            {
                "summary": analysis["summary"],
                "portfolio": analysis["portfolio"],
                "sector": analysis["sector"],
                "industry": analysis["industry"],
                "market_cap": analysis["market_cap"],
                "benchmarks": analysis["benchmarks"],
                "risk": risk,
                "style": style,
                "returns": returns,
                "mapping": meta.get("mapping"),
                "unresolved_names": meta.get("unresolved_names", []),
                "report_path": output_pdf,
            }
        )
