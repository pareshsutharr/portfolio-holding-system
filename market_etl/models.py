"""SQLAlchemy models for market reference and time-series data."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Date,
    DateTime,
    Boolean,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    JSON,
    Numeric,
    Sequence,
    String,
    Text,
    BigInteger,
    UniqueConstraint,
    CheckConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SectorIndustryMapping(Base):
    __tablename__ = "sector_industry_mapping"

    sector: Mapped[str] = mapped_column(String(150), primary_key=True)
    industry: Mapped[str] = mapped_column(String(200), primary_key=True)


class CompanyMaster(Base):
    __tablename__ = "company_master"

    isin: Mapped[str] = mapped_column(String(20), primary_key=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    sector: Mapped[Optional[str]] = mapped_column(String(150))
    industry: Mapped[Optional[str]] = mapped_column(String(200))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["sector", "industry"],
            ["sector_industry_mapping.sector", "sector_industry_mapping.industry"],
            name="fk_company_sector_industry",
        ),
    )


class DailyMarketData(Base):
    __tablename__ = "daily_market_data"

    isin: Mapped[str] = mapped_column(
        String(20), ForeignKey("company_master.isin"), primary_key=True
    )
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    close_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    market_cap: Mapped[Optional[Decimal]] = mapped_column(Numeric(22, 4))
    volume: Mapped[Optional[Decimal]] = mapped_column(Numeric(22, 3))
    turnover: Mapped[Optional[Decimal]] = mapped_column(Numeric(22, 6))

    __table_args__ = (Index("ix_daily_market_data_trade_date", "trade_date"),)


class Fundamental(Base):
    __tablename__ = "fundamentals"

    isin: Mapped[str] = mapped_column(
        String(20), ForeignKey("company_master.isin"), primary_key=True
    )
    financial_year: Mapped[int] = mapped_column(primary_key=True)
    roe: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    roce: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    interest_cover: Mapped[Optional[Decimal]] = mapped_column(Numeric(16, 4))
    debt_equity: Mapped[Optional[Decimal]] = mapped_column(Numeric(16, 4))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class BenchmarkData(Base):
    __tablename__ = "benchmark_data"

    index_name: Mapped[str] = mapped_column(String(100), primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    close_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)

    __table_args__ = (Index("ix_benchmark_data_trade_date", "trade_date"),)


class IndexSectorAllocation(Base):
    """A dated, immutable-by-date sector snapshot from an official index factsheet."""

    __tablename__ = "index_sector_allocations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    index_name: Mapped[str] = mapped_column(String(32), nullable=False)
    sector: Mapped[str] = mapped_column(String(200), nullable=False)
    weight_percent: Mapped[Decimal] = mapped_column(Numeric(7, 4), nullable=False)
    factsheet_date: Mapped[date] = mapped_column(Date, nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_file: Mapped[str] = mapped_column(String(255), nullable=False)
    row_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("index_name", "sector", "factsheet_date", name="uq_index_sector_allocation_snapshot"),
        CheckConstraint("index_name in ('NIFTY50', 'NIFTYMIDCAP150', 'NIFTY500')", name="ck_index_sector_allocation_index"),
        CheckConstraint("weight_percent >= 0 and weight_percent <= 100", name="ck_index_sector_allocation_weight"),
        Index("ix_index_sector_allocations_latest", "index_name", "factsheet_date"),
    )


class IngestionRun(Base):
    """Observable status and counts for every sector-factsheet ingestion attempt."""

    __tablename__ = "ingestion_runs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    method_used: Mapped[Optional[str]] = mapped_column(String(32))
    records_fetched: Mapped[int] = mapped_column(nullable=False, default=0)
    inserted: Mapped[int] = mapped_column(nullable=False, default=0)
    updated: Mapped[int] = mapped_column(nullable=False, default=0)
    duplicates_skipped: Mapped[int] = mapped_column(nullable=False, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[Optional[str]] = mapped_column(Text)


class ClientOnboarding(Base):
    """Tokenized client-information invitation and its submitted form."""

    __tablename__ = "client_onboarding"

    token: Mapped[str] = mapped_column(String(100), primary_key=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    client_name: Mapped[Optional[str]] = mapped_column(String(255))
    client_email: Mapped[Optional[str]] = mapped_column(String(255))
    favorite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    form_data: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class UserAccount(Base):
    """Authenticated administrator or client account."""

    __tablename__ = "user_accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="client", index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


report_number_seq = Sequence("portfolio_report_number_seq", start=1, metadata=Base.metadata)


def format_report_number(number: int | None) -> str | None:
    """Render a sequential report number as the client-facing code, e.g. JBV-GA-001."""

    if number is None:
        return None
    return f"JBV-GA-{number:03d}"


class PortfolioRun(Base):
    """Persistent ownership and summary metadata for an analysis artifact."""

    __tablename__ = "portfolio_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("user_accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("user_accounts.id"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="uploaded")
    summary: Mapped[Optional[dict]] = mapped_column(JSON)
    report_number: Mapped[Optional[int]] = mapped_column(BigInteger, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    __table_args__ = (Index("ix_portfolio_runs_owner_created", "owner_id", "created_at"),)


class ReportConfiguration(Base):
    """Admin-managed global or per-client report presentation settings."""

    __tablename__ = "report_configurations"

    owner_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False, default="Portfolio Analysis Report")
    subtitle: Mapped[str] = mapped_column(String(500), nullable=False, default="A complete view of portfolio structure, risk, style, and performance.")
    sections: Mapped[dict] = mapped_column(JSON, nullable=False)
    benchmarks: Mapped[Optional[dict]] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
