"""Independently runnable daily local ingestion scheduler."""

from apscheduler.schedulers.blocking import BlockingScheduler

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
    sessions = build_session_factory(engine)
    scheduler = BlockingScheduler(timezone="Asia/Kolkata")
    scheduler.add_job(lambda: ingest_all(sessions), "cron", hour=7, minute=0, id="daily-sector-allocations", max_instances=1, coalesce=True)
    scheduler.start()


if __name__ == "__main__":
    main()
