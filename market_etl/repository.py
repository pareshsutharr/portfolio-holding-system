"""PostgreSQL upsert operations used by ETL services."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from market_etl.models import (
    BenchmarkData,
    CompanyMaster,
    DailyMarketData,
    Fundamental,
    SectorIndustryMapping,
)

CHUNK_SIZE = 2_000


def _chunks(rows: list[dict[str, Any]]) -> Iterable[list[dict[str, Any]]]:
    for start in range(0, len(rows), CHUNK_SIZE):
        yield rows[start : start + CHUNK_SIZE]


def upsert_mappings(session: Session, rows: list[dict[str, Any]]) -> None:
    for chunk in _chunks(rows):
        statement = insert(SectorIndustryMapping).values(chunk)
        session.execute(statement.on_conflict_do_nothing())


def upsert_companies(session: Session, rows: list[dict[str, Any]]) -> None:
    for chunk in _chunks(rows):
        statement = insert(CompanyMaster).values(chunk)
        excluded = statement.excluded
        session.execute(
            statement.on_conflict_do_update(
                index_elements=["isin"],
                set_={
                    "company_name": excluded.company_name,
                    "sector": func.coalesce(excluded.sector, CompanyMaster.sector),
                    "industry": func.coalesce(excluded.industry, CompanyMaster.industry),
                },
            )
        )


def upsert_market_data(session: Session, rows: list[dict[str, Any]]) -> None:
    for chunk in _chunks(rows):
        statement = insert(DailyMarketData).values(chunk)
        excluded = statement.excluded
        session.execute(
            statement.on_conflict_do_update(
                index_elements=["isin", "trade_date"],
                set_={
                    "close_price": excluded.close_price,
                    "market_cap": excluded.market_cap,
                    "volume": excluded.volume,
                    "turnover": excluded.turnover,
                },
            )
        )


def upsert_fundamentals(session: Session, rows: list[dict[str, Any]]) -> None:
    for chunk in _chunks(rows):
        statement = insert(Fundamental).values(chunk)
        excluded = statement.excluded
        session.execute(
            statement.on_conflict_do_update(
                index_elements=["isin", "financial_year"],
                set_={
                    "roe": excluded.roe,
                    "roce": excluded.roce,
                    "interest_cover": excluded.interest_cover,
                    "debt_equity": excluded.debt_equity,
                },
            )
        )


def upsert_benchmark(session: Session, rows: list[dict[str, Any]]) -> None:
    for chunk in _chunks(rows):
        statement = insert(BenchmarkData).values(chunk)
        excluded = statement.excluded
        session.execute(
            statement.on_conflict_do_update(
                index_elements=["index_name", "trade_date"],
                set_={"close_price": excluded.close_price},
            )
        )
