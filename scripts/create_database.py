"""Create all market_data tables in an existing PostgreSQL database."""

from market_etl.config import Settings
from market_etl.database import build_engine
from market_etl.logging_config import configure_logging
from market_etl.models import Base


def main() -> None:
    settings = Settings.from_env()
    configure_logging(settings.log_level)
    engine = build_engine(settings.database_url)
    Base.metadata.create_all(engine)
    print("Database tables created successfully.")


if __name__ == "__main__":
    main()

