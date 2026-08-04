"""Upload all Data Center files into private Supabase Storage."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from sqlalchemy.dialects.postgresql import insert

from api.data_center import ENTRIES, ROOT
from market_etl.config import Settings
from market_etl.database import build_engine, build_session_factory
from market_etl.models import Base, ManagedDataAsset
from market_etl.storage_assets import SupabaseStorage, asset_object_path


def source_files(entry) -> list[Path]:
    if entry.kind == "single_file":
        return [ROOT / entry.paths[0]]
    folder = ROOT / entry.paths[0]
    return sorted(p for p in folder.glob("*") if p.is_file() and p.suffix.lower() in entry.extensions)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--category", action="append", help="Upload only this category (repeatable)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    storage = SupabaseStorage.from_env()
    if storage is None and not args.dry_run:
        raise SystemExit("SUPABASE_URL and SUPABASE_SECRET_KEY are required")

    selected = [entry for entry in ENTRIES if not args.category or entry.key in args.category]
    files = [(entry, path) for entry in selected for path in source_files(entry) if path.exists()]
    print(f"Found {len(files)} managed files ({sum(p.stat().st_size for _, p in files):,} bytes)")
    if args.dry_run:
        for entry, path in files:
            print(f"DRY RUN {entry.key}: {path}")
        return

    engine = build_engine(Settings.from_env().database_url)
    Base.metadata.create_all(engine)
    sessions = build_session_factory(engine)
    for number, (entry, path) in enumerate(files, 1):
        object_path = asset_object_path(entry.key, path.name)
        asset = storage.upload_bytes(object_path, path.read_bytes(), path.name)
        with sessions.begin() as session:
            statement = insert(ManagedDataAsset).values(
                object_path=asset.object_path,
                category_key=entry.key,
                bucket_id=storage.bucket,
                original_name=asset.original_name,
                content_type=asset.content_type,
                size_bytes=asset.size_bytes,
                sha256=asset.sha256,
            ).on_conflict_do_update(
                index_elements=[ManagedDataAsset.object_path],
                set_={
                    "category_key": entry.key,
                    "bucket_id": storage.bucket,
                    "original_name": asset.original_name,
                    "content_type": asset.content_type,
                    "size_bytes": asset.size_bytes,
                    "sha256": asset.sha256,
                },
            )
            session.execute(statement)
        print(f"[{number}/{len(files)}] uploaded {object_path}")


if __name__ == "__main__":
    main()
