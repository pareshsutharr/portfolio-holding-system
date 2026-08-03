"""Load the refreshed ACE workbook and update the NIFTY 50 benchmark."""

import argparse
from pathlib import Path

from market_etl.config import Settings
from market_etl.database import build_engine, build_session_factory
from market_etl.logging_config import configure_logging
from market_etl.services import BenchmarkService, DailyUpdateService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, help="Refreshed ACE Equity Excel file")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = Settings.from_env()
    configure_logging(settings.log_level)
    engine = build_engine(settings.database_url)
    benchmark = BenchmarkService(settings.benchmark_symbol, settings.benchmark_name)
    service = DailyUpdateService(build_session_factory(engine), benchmark)
    service.run(args.file or settings.daily_ace_file)


if __name__ == "__main__":
    main()

