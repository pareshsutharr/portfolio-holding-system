"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

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
        return cls(
            database_url=os.getenv(
                "DATABASE_URL",
                "postgresql+psycopg://postgres:postgres@localhost:5432/market_data",
            ),
            daily_ace_file=Path(os.getenv("DAILY_ACE_FILE", "Daily_Data.xlsx")),
            historical_data_dir=Path(os.getenv("HISTORICAL_DATA_DIR", "Data")),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            benchmark_symbol=os.getenv("BENCHMARK_SYMBOL", "^NSEI"),
            benchmark_name=os.getenv("BENCHMARK_NAME", "NIFTY 50"),
        )
