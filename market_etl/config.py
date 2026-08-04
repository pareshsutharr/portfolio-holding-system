"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    database_url: str
    daily_ace_file: Path
    historical_data_dir: Path
    log_level: str
    benchmark_symbol: str
    benchmark_name: str

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        database_url = os.getenv("DATABASE_URL", "").strip()
        if not database_url:
            raise RuntimeError("DATABASE_URL is required and must point to Supabase PostgreSQL")
        hostname = urlparse(database_url.replace("postgresql+psycopg://", "postgresql://", 1)).hostname or ""
        if not hostname.endswith(".supabase.com"):
            raise RuntimeError("DATABASE_URL must point to a Supabase PostgreSQL host")
        return cls(
            database_url=database_url,
            daily_ace_file=Path(os.getenv("DAILY_ACE_FILE", "Daily_Data.xlsx")),
            historical_data_dir=Path(os.getenv("HISTORICAL_DATA_DIR", "Data")),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            benchmark_symbol=os.getenv("BENCHMARK_SYMBOL", "^NSEI"),
            benchmark_name=os.getenv("BENCHMARK_NAME", "NIFTY 50"),
        )
