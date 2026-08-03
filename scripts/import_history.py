"""One-time import of historical ACE Equity workbooks."""

import argparse
from pathlib import Path

from market_etl.config import Settings
from market_etl.database import build_engine, build_session_factory
from market_etl.logging_config import configure_logging
from market_etl.services import HistoricalImportService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, help="Folder searched recursively for .xlsx files")
    parser.add_argument(
        "--master-file",
        type=Path,
        help="Optional current ACE file containing sector, industry, and fundamentals",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = Settings.from_env()
    configure_logging(settings.log_level)
    engine = build_engine(settings.database_url)
    service = HistoricalImportService(build_session_factory(engine))
    service.run(args.data_dir or settings.historical_data_dir, args.master_file)


if __name__ == "__main__":
    main()

