"""Download missing NIFTY 50 daily closes into benchmark_data."""

from market_etl.config import Settings
from market_etl.database import build_engine, build_session_factory
from market_etl.logging_config import configure_logging
from market_etl.services import BenchmarkService


def main() -> None:
    settings = Settings.from_env()
    configure_logging(settings.log_level)
    engine = build_engine(settings.database_url)
    sessions = build_session_factory(engine)
    service = BenchmarkService(settings.benchmark_symbol, settings.benchmark_name)
    with sessions.begin() as session:
        count = service.update(session)
    print(f"NIFTY 50 benchmark update complete: {count} rows processed.")


if __name__ == "__main__":
    main()
