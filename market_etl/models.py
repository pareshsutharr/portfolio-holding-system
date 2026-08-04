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
    String,
    Text,
    BigInteger,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ManagedDataAsset(Base):
    """Registry for private reference files stored in Supabase Storage."""

    __tablename__ = "managed_data_assets"

    object_path: Mapped[str] = mapped_column(Text, primary_key=True)
    category_key: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    bucket_id: Mapped[str] = mapped_column(Text, nullable=False)
    original_name: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(Text, nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


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
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
