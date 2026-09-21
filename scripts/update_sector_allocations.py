"""Run all official NIFTY sector-allocation ingestions once."""

from market_etl.config import Settings
from market_etl.database import build_engine, build_session_factory
from market_etl.logging_config import configure_logging
from market_etl.models import Base
from market_etl.sector_allocations import ingest_all


def main() -> None:
    settings = Settings.from_env()
    configure_logging(settings.log_level)
    engine = build_engine(settings.database_url)
    Base.metadata.create_all(engine)
    result = ingest_all(build_session_factory(engine), wait_for_lock=True)
    print(result)
    if result["status"] == "failed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
