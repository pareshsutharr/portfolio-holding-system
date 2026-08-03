"""Orchestration services for historical and daily loads."""

from __future__ import annotations

import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import yfinance as yf
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from market_etl.models import BenchmarkData
from market_etl.readers import read_daily_ace, read_historical_ace
from market_etl.repository import (
    upsert_benchmark,
    upsert_companies,
    upsert_fundamentals,
    upsert_mappings,
    upsert_market_data,
)

LOGGER = logging.getLogger(__name__)


def _value(value: Any) -> Any:
    return None if pd.isna(value) else value


def _records(frame: pd.DataFrame, columns: list[str]) -> list[dict[str, Any]]:
    available = frame.reindex(columns=columns)
    return [
        {key: _value(value) for key, value in row.items()}
        for row in available.to_dict("records")
    ]


def load_ace_frame(session: Session, frame: pd.DataFrame, *, include_fundamentals: bool) -> None:
    enriched = {"sector", "industry"}.issubset(frame.columns)
    if enriched:
        mappings = (
            frame.dropna(subset=["sector", "industry"])[["sector", "industry"]]
            .drop_duplicates()
        )
        upsert_mappings(session, _records(mappings, ["sector", "industry"]))

    company_columns = ["isin", "company_name"]
    companies = frame
    if enriched:
        company_columns += ["sector", "industry"]
        companies = frame.sort_values("trade_date").drop_duplicates("isin", keep="last")
    else:
        companies = frame.drop_duplicates("isin", keep="last")
    upsert_companies(session, _records(companies, company_columns))

    market_columns = ["isin", "trade_date", "close_price", "market_cap", "volume", "turnover"]
    market = frame.dropna(subset=["isin", "trade_date"]).drop_duplicates(
        ["isin", "trade_date"], keep="last"
    )
    upsert_market_data(session, _records(market, market_columns))

    if include_fundamentals and "financial_year" in frame:
        fundamentals = frame.dropna(subset=["isin", "financial_year"]).copy()
        fundamentals["financial_year"] = fundamentals["financial_year"].astype(int)
        fundamentals = fundamentals.drop_duplicates(
            ["isin", "financial_year"], keep="last"
        )
        columns = [
            "isin", "financial_year", "roe", "roce", "interest_cover", "debt_equity"
        ]
        upsert_fundamentals(session, _records(fundamentals, columns))


class HistoricalImportService:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def run(self, data_dir: Path, master_file: Path | None = None) -> None:
        files = sorted(data_dir.rglob("*.xlsx"))
        files = [path for path in files if not path.name.startswith("~$")]
        if not files:
            raise FileNotFoundError(f"No Excel files found under {data_dir}")

        with self.session_factory.begin() as session:
            if master_file:
                LOGGER.info("Loading company classifications and fundamentals from %s", master_file)
                load_ace_frame(session, read_daily_ace(master_file), include_fundamentals=True)
            for index, path in enumerate(files, start=1):
                LOGGER.info("Importing historical file %s/%s: %s", index, len(files), path)
                load_ace_frame(session, read_historical_ace(path), include_fundamentals=False)


class BenchmarkService:
    def __init__(self, symbol: str, index_name: str) -> None:
        self.symbol = symbol
        self.index_name = index_name

    def update(self, session: Session) -> int:
        latest = session.scalar(
            select(func.max(BenchmarkData.trade_date)).where(
                BenchmarkData.index_name == self.index_name
            )
        )
        start = latest + timedelta(days=1) if latest else date(1990, 1, 1)
        end = date.today() + timedelta(days=1)
        if start >= end:
            return 0
        data = yf.download(
            self.symbol,
            start=start.isoformat(),
            end=end.isoformat(),
            auto_adjust=False,
            progress=False,
        )
        if data.empty:
            LOGGER.warning("Yahoo Finance returned no benchmark rows")
            return 0
        close = data["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        rows = [
            {
                "index_name": self.index_name,
                "trade_date": timestamp.date(),
                "close_price": float(price),
            }
            for timestamp, price in close.dropna().items()
        ]
        upsert_benchmark(session, rows)
        return len(rows)


class DailyUpdateService:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        benchmark_service: BenchmarkService,
    ) -> None:
        self.session_factory = session_factory
        self.benchmark_service = benchmark_service

    def run(self, ace_file: Path) -> None:
        frame = read_daily_ace(ace_file)
        with self.session_factory.begin() as session:
            load_ace_frame(session, frame, include_fundamentals=True)
        benchmark_count = 0
        try:
            with self.session_factory.begin() as session:
                benchmark_count = self.benchmark_service.update(session)
        except Exception:
            LOGGER.exception(
                "ACE data was updated, but the benchmark refresh failed; "
                "existing benchmark history will be retained"
            )
        LOGGER.info(
            "Daily update complete: %s ACE rows, %s benchmark rows",
            len(frame),
            benchmark_count,
        )
