"""Server-only Supabase Storage access for managed reference datasets."""

from __future__ import annotations

import hashlib
import mimetypes
import os
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import quote

import requests
from sqlalchemy import select

from market_etl.database import build_session_factory
from market_etl.models import ManagedDataAsset


DEFAULT_BUCKET = "portfolio-reference-data"


@dataclass(frozen=True)
class StoredAsset:
    object_path: str
    original_name: str
    content_type: str
    size_bytes: int
    sha256: str


class SupabaseStorage:
    def __init__(self, url: str, secret_key: str, bucket: str = DEFAULT_BUCKET):
        self.url = url.rstrip("/")
        self.secret_key = secret_key
        self.bucket = bucket

    @classmethod
    def from_env(cls) -> "SupabaseStorage | None":
        url = os.getenv("SUPABASE_URL", "").strip()
        key = os.getenv("SUPABASE_SECRET_KEY", "").strip() or os.getenv(
            "SUPABASE_SERVICE_ROLE_KEY", ""
        ).strip()
        if not url or not key:
            return None
        return cls(url, key, os.getenv("SUPABASE_STORAGE_BUCKET", DEFAULT_BUCKET))

    @property
    def headers(self) -> dict[str, str]:
        return {"apikey": self.secret_key, "Authorization": f"Bearer {self.secret_key}"}

    def _object_url(self, object_path: str) -> str:
        safe = quote(str(PurePosixPath(object_path)), safe="/")
        return f"{self.url}/storage/v1/object/{quote(self.bucket, safe='')}/{safe}"

    def upload_bytes(self, object_path: str, data: bytes, filename: str) -> StoredAsset:
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        response = requests.post(
            self._object_url(object_path),
            headers={**self.headers, "Content-Type": content_type, "x-upsert": "true"},
            data=data,
            timeout=180,
        )
        response.raise_for_status()
        return StoredAsset(
            object_path=object_path,
            original_name=Path(filename).name,
            content_type=content_type,
            size_bytes=len(data),
            sha256=hashlib.sha256(data).hexdigest(),
        )

    def download(self, object_path: str, destination: Path) -> Path:
        response = requests.get(self._object_url(object_path), headers=self.headers, timeout=180)
        response.raise_for_status()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(response.content)
        return destination

    def delete(self, object_paths: list[str]) -> None:
        if not object_paths:
            return
        response = requests.delete(
            f"{self.url}/storage/v1/object/{quote(self.bucket, safe='')}",
            headers={**self.headers, "Content-Type": "application/json"},
            json={"prefixes": object_paths},
            timeout=60,
        )
        response.raise_for_status()


def asset_object_path(category_key: str, filename: str) -> str:
    return f"managed/{category_key}/{Path(filename).name}"


STYLE_CATEGORIES = {
    "growth_data",
    "value_data",
    "quality_data",
    "liquidity_data",
    "daily_prices_nse",
    "daily_prices_bse",
    "nifty50_index",
}


def hydrate_style_assets(engine, cache_root: Path = Path("/tmp/portfolio-reference-data")) -> None:
    """Download the style inputs needed by a serverless analysis into /tmp."""
    storage = SupabaseStorage.from_env()
    if storage is None:
        return
    sessions = build_session_factory(engine)
    with sessions() as session:
        assets = session.scalars(
            select(ManagedDataAsset).where(ManagedDataAsset.category_key.in_(STYLE_CATEGORIES))
        ).all()

    # Price history consumes only the latest 38 monthly snapshots.
    selected = []
    for category in STYLE_CATEGORIES:
        category_assets = [asset for asset in assets if asset.category_key == category]
        if category.startswith("daily_prices_"):
            def month_key(asset):
                stem = Path(asset.original_name).stem
                return (stem[4:8], stem[2:4]) if len(stem) == 8 and stem.isdigit() else ("", "")
            category_assets = sorted(category_assets, key=month_key)[-38:]
        selected.extend(category_assets)

    for asset in selected:
        destination = cache_root / asset.category_key / asset.original_name
        if destination.exists() and destination.stat().st_size == asset.size_bytes:
            continue
        storage.download(asset.object_path, destination)
