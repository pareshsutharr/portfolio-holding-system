"""Create or promote an administrator account."""

from __future__ import annotations

import argparse
import getpass
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.auth import hash_password
from market_etl.config import Settings
from market_etl.database import build_engine
from market_etl.models import Base, UserAccount


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a Northstar administrator")
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()
    password = getpass.getpass("Admin password (minimum 8 characters): ")
    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match")
    engine = build_engine(Settings.from_env().database_url)
    Base.metadata.create_all(engine)
    email = args.email.strip().lower()
    with Session(engine) as session:
        user = session.scalar(select(UserAccount).where(UserAccount.email == email))
        if user:
            user.full_name = args.name.strip()
            user.password_hash = hash_password(password)
            user.role = "admin"
            user.is_active = True
        else:
            session.add(UserAccount(id=str(uuid.uuid4()), email=email, full_name=args.name.strip(), password_hash=hash_password(password), role="admin"))
        session.commit()
    print(f"Administrator ready: {email}")


if __name__ == "__main__":
    main()
