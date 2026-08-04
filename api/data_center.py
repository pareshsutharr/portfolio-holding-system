"""Admin data-management API: list, upload, replace, and delete the raw
reference/master files the analysis pipeline reads from disk.

Every managed path below is grounded in config.py / portfolio_returns.py --
this does not invent new locations. Destructive operations always back the
previous file up under runtime/data-center-backups/ first, so nothing is
unrecoverably lost through the UI.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert

from market_etl.config import Settings
from market_etl.database import build_engine, build_session_factory
from market_etl.models import ManagedDataAsset
from market_etl.storage_assets import SupabaseStorage, asset_object_path

ROOT = Path(__file__).resolve().parents[1]
BACKUP_DIR = Path("/tmp/data-center-backups") if os.getenv("VERCEL") else ROOT / "runtime" / "data-center-backups"
MAX_UPLOAD_BYTES = 25 * 1024 * 1024


@dataclass(frozen=True)
class DataEntry:
    key: str
    label: str
    description: str
    frequency: str  # "fixed" | "quarterly" | "yearly" | "daily" | "monthly" | "undecided"
    kind: str  # "single_file" | "file_folder"
    paths: tuple[str, ...]  # relative to ROOT; single_file entries with >1 path are kept in sync
    extensions: tuple[str, ...]
    consumers: str = ""


ENTRIES: list[DataEntry] = [
    # -- Fixed reference data -------------------------------------------------
    DataEntry(
        key="isin_master",
        label="ISIN master",
        description="Company master list keyed by ISIN.",
        frequency="fixed",
        kind="single_file",
        paths=("test_files/isin.xlsx",),
        extensions=(".xlsx", ".xls"),
        consumers="portfolio_service.py holdings parsing",
    ),
    DataEntry(
        key="sector_industry_map",
        label="Sector → industry mapping",
        description="Canonical sector/industry taxonomy.",
        frequency="fixed",
        kind="single_file",
        paths=("sector_mapping.json",),
        extensions=(".json",),
        consumers="sector_mapping.py",
    ),
    DataEntry(
        key="isin_sector_map",
        label="ISIN → sector mapping",
        description="Per-company sector assignment.",
        frequency="fixed",
        kind="single_file",
        paths=("test_files/sector_mapping.xlsx",),
        extensions=(".xlsx", ".xls"),
        consumers="sector_industry.py",
    ),
    DataEntry(
        key="bse500_constituents",
        label="BSE 500 constituents",
        description="Reference universe for BSE-listed names.",
        frequency="fixed",
        kind="single_file",
        paths=("test_files/bse500.xlsx",),
        extensions=(".xlsx", ".xls"),
        consumers="market_cap.py",
    ),
    # -- Quarterly --------------------------------------------------------------
    DataEntry(
        key="market_cap",
        label="Market capitalization (MCap)",
        description="Latest free-float / full market cap per company.",
        frequency="quarterly",
        kind="single_file",
        paths=("test_files/MCap.xlsx",),
        extensions=(".xlsx", ".xls"),
        consumers="market_cap.py",
    ),
    # -- Yearly -------------------------------------------------------------
    DataEntry(
        key="sector_weight_nifty50",
        label="Sector weights — Nifty 50",
        description="Sector allocation % from the Nifty 50 factsheet.",
        frequency="yearly",
        kind="single_file",
        paths=("benchmark/output/nifty50_sector_allocation.csv",),
        extensions=(".csv",),
        consumers="benchmark_analysis.py",
    ),
    DataEntry(
        key="sector_weight_nifty150",
        label="Sector weights — Nifty Midcap 150",
        description="Sector allocation % from the Nifty Midcap 150 factsheet.",
        frequency="yearly",
        kind="single_file",
        paths=("benchmark/output/nifty_midcap_150_sector_allocation.csv",),
        extensions=(".csv",),
        consumers="benchmark_analysis.py",
    ),
    DataEntry(
        key="sector_weight_nifty500",
        label="Sector weights — Nifty 500",
        description="Sector allocation % from the Nifty 500 factsheet.",
        frequency="yearly",
        kind="single_file",
        paths=("benchmark/output/nifty500_sector_allocation.csv",),
        extensions=(".csv",),
        consumers="benchmark_analysis.py",
    ),
    DataEntry(
        key="quality_data",
        label="Quality",
        description="ROE, ROCE, debt/equity, interest cover style inputs.",
        frequency="yearly",
        kind="single_file",
        paths=("Portfolio Analyzer Data/Data_Quality.xlsx",),
        extensions=(".xlsx", ".xls"),
        consumers="stock_style_scoring.py (quality factor)",
    ),
    # -- Daily ----------------------------------------------------------------
    DataEntry(
        key="nifty50_index",
        label="Nifty 50 index data",
        description="Nifty 50 constituent list and prices.",
        frequency="daily",
        kind="single_file",
        paths=("Data_Nifty_50.csv", "Portfolio Analyzer Data/Data_Nifty_50.csv"),
        extensions=(".csv",),
        consumers="portfolio_returns.py, stock_style_market.py",
    ),
    DataEntry(
        key="nifty150_index",
        label="Nifty 150 index data",
        description="Nifty Midcap 150 constituent list and prices.",
        frequency="daily",
        kind="single_file",
        paths=("Data_Nifty_150.csv",),
        extensions=(".csv",),
        consumers="portfolio_returns.py",
    ),
    DataEntry(
        key="nifty500_index",
        label="Nifty 500 index data",
        description="Nifty 500 constituent list and prices.",
        frequency="daily",
        kind="single_file",
        paths=("Data_Nifty_500.csv",),
        extensions=(".csv",),
        consumers="portfolio_returns.py",
    ),
    DataEntry(
        key="momentum_feed",
        label="Momentum (daily ACE feed)",
        description="Daily ACE workbook driving 6M/12M return and 200-DMA momentum scoring.",
        frequency="daily",
        kind="single_file",
        paths=("Daily_Data.xlsx",),
        extensions=(".xlsx", ".xls"),
        consumers="scripts/daily_update.py, stock_style_scoring.py (momentum factor)",
    ),
    DataEntry(
        key="daily_prices_nse",
        label="Daily prices — NSE",
        description="One dated workbook per trading day.",
        frequency="daily",
        kind="file_folder",
        paths=("Portfolio Analyzer Data/Data_NSE",),
        extensions=(".xlsx", ".xls"),
        consumers="stock_style_market.py",
    ),
    DataEntry(
        key="daily_prices_bse",
        label="Daily prices — BSE",
        description="One dated workbook per trading day.",
        frequency="daily",
        kind="file_folder",
        paths=("Portfolio Analyzer Data/Data_BSE",),
        extensions=(".xlsx", ".xls"),
        consumers="stock_style_market.py",
    ),
    DataEntry(
        key="liquidity_data",
        label="Liquidity",
        description="Turnover / volume style inputs (daily-derived).",
        frequency="daily",
        kind="single_file",
        paths=("Portfolio Analyzer Data/Data_Liquidity.xlsx",),
        extensions=(".xlsx", ".xls"),
        consumers="stock_style_scoring.py (liquidity factor)",
    ),
    # -- Not yet decided ------------------------------------------------------
    DataEntry(
        key="growth_data",
        label="Growth",
        description="Revenue/PAT/EPS CAGR and ROE/ROCE style inputs.",
        frequency="undecided",
        kind="single_file",
        paths=("Portfolio Analyzer Data/Data_Growth.xlsx",),
        extensions=(".xlsx", ".xls"),
        consumers="stock_style_scoring.py (growth factor)",
    ),
    DataEntry(
        key="value_data",
        label="Value",
        description="P/E, P/B, EV/EBITDA, dividend yield style inputs.",
        frequency="undecided",
        kind="single_file",
        paths=("Portfolio Analyzer Data/Data_Value.xlsx",),
        extensions=(".xlsx", ".xls"),
        consumers="stock_style_scoring.py (value factor)",
    ),
    # -- Monthly ----------------------------------------------------------------
    DataEntry(
        key="historical_monthly",
        label="Historical monthly workbooks",
        description="One ACE workbook per month, used for the one-time historical database import.",
        frequency="monthly",
        kind="file_folder",
        paths=("Data",),
        extensions=(".xlsx", ".xls"),
        consumers="scripts/import_history.py",
    ),
]

ENTRIES_BY_KEY = {entry.key: entry for entry in ENTRIES}

router = APIRouter(prefix="/api/data-center", tags=["data-center"])


def _storage() -> SupabaseStorage | None:
    return SupabaseStorage.from_env()


def _sessions():
    return build_session_factory(build_engine(Settings.from_env().database_url))


def _remote_assets(category_key: str) -> list[dict]:
    if _storage() is None:
        return []
    with _sessions()() as session:
        rows = session.scalars(
            select(ManagedDataAsset)
            .where(ManagedDataAsset.category_key == category_key)
            .order_by(ManagedDataAsset.original_name.desc())
        ).all()
    return [
        {
            "name": row.original_name,
            "size_bytes": row.size_bytes,
            "modified_at": row.updated_at.isoformat(),
        }
        for row in rows
    ]


def _register_remote(entry: DataEntry, filename: str, data: bytes) -> None:
    storage = _storage()
    if storage is None:
        return
    asset = storage.upload_bytes(asset_object_path(entry.key, filename), data, filename)
    with _sessions().begin() as session:
        session.execute(
            insert(ManagedDataAsset)
            .values(
                object_path=asset.object_path,
                category_key=entry.key,
                bucket_id=storage.bucket,
                original_name=asset.original_name,
                content_type=asset.content_type,
                size_bytes=asset.size_bytes,
                sha256=asset.sha256,
            )
            .on_conflict_do_update(
                index_elements=[ManagedDataAsset.object_path],
                set_={
                    "original_name": asset.original_name,
                    "content_type": asset.content_type,
                    "size_bytes": asset.size_bytes,
                    "sha256": asset.sha256,
                    "updated_at": datetime.now(timezone.utc),
                },
            )
        )


def _delete_remote(entry: DataEntry, filename: str) -> None:
    storage = _storage()
    if storage is None:
        return
    object_path = asset_object_path(entry.key, filename)
    storage.delete([object_path])
    with _sessions().begin() as session:
        session.execute(delete(ManagedDataAsset).where(ManagedDataAsset.object_path == object_path))


def _entry(key: str) -> DataEntry:
    entry = ENTRIES_BY_KEY.get(key)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Unknown data category '{key}'")
    return entry


def _safe_name(name: str) -> str:
    candidate = Path(name).name
    if not candidate or candidate in {".", ".."} or "/" in name or "\\" in name:
        raise HTTPException(status_code=400, detail="Invalid file name")
    return candidate


def _validate_extension(entry: DataEntry, filename: str) -> None:
    suffix = Path(filename).suffix.lower()
    if suffix not in entry.extensions:
        allowed = ", ".join(entry.extensions)
        raise HTTPException(status_code=415, detail=f"{entry.label} only accepts {allowed} files")


def _backup(path: Path, category_key: str) -> None:
    if not path.exists():
        return
    target_dir = BACKUP_DIR / category_key
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    shutil.copy2(path, target_dir / f"{stamp}__{path.name}")


def _file_info(path: Path) -> dict | None:
    if not path.exists() or not path.is_file():
        return None
    stat = path.stat()
    return {
        "name": path.name,
        "size_bytes": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
    }


def _folder_files(path: Path) -> list[dict]:
    if not path.exists() or not path.is_dir():
        return []
    files = [info for child in path.iterdir() if child.is_file() and (info := _file_info(child))]
    return sorted(files, key=lambda item: item["name"], reverse=True)


def _entry_payload(entry: DataEntry) -> dict:
    payload = {
        "key": entry.key,
        "label": entry.label,
        "description": entry.description,
        "frequency": entry.frequency,
        "kind": entry.kind,
        "extensions": list(entry.extensions),
        "consumers": entry.consumers,
    }
    remote = _remote_assets(entry.key)
    if entry.kind == "single_file":
        primary = ROOT / entry.paths[0]
        payload["file"] = remote[0] if remote else _file_info(primary)
        payload["synced_paths"] = list(entry.paths) if len(entry.paths) > 1 else []
    else:
        folder = ROOT / entry.paths[0]
        files = remote or _folder_files(folder)
        payload["files"] = files
        payload["file_count"] = len(files)
        payload["total_size_bytes"] = sum(item["size_bytes"] for item in files)
    return payload


@router.get("")
def list_data_center() -> dict:
    return {"categories": [_entry_payload(entry) for entry in ENTRIES]}


async def _read_upload(upload: UploadFile) -> bytes:
    data = await upload.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds the 25 MB upload limit")
    return data


@router.post("/{key}/file")
async def upload_single_file(key: str, file: UploadFile = File(...)) -> dict:
    entry = _entry(key)
    if entry.kind != "single_file":
        raise HTTPException(status_code=400, detail=f"{entry.label} manages multiple files; use the folder endpoint")
    _validate_extension(entry, file.filename or "")
    data = await _read_upload(file)
    if _storage() is not None:
        _register_remote(entry, Path(entry.paths[0]).name, data)
        return _entry_payload(entry)
    for relative in entry.paths:
        target = ROOT / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        _backup(target, entry.key)
        target.write_bytes(data)
    return _entry_payload(entry)


@router.delete("/{key}/file")
def delete_single_file(key: str) -> dict:
    entry = _entry(key)
    if entry.kind != "single_file":
        raise HTTPException(status_code=400, detail=f"{entry.label} manages multiple files; use the folder endpoint")
    primary = ROOT / entry.paths[0]
    if _storage() is not None:
        remote = _remote_assets(entry.key)
        if not remote:
            raise HTTPException(status_code=404, detail=f"{entry.label} has no file to delete")
        _delete_remote(entry, remote[0]["name"])
        return _entry_payload(entry)
    if not primary.exists():
        raise HTTPException(status_code=404, detail=f"{entry.label} has no file to delete")
    for relative in entry.paths:
        target = ROOT / relative
        _backup(target, entry.key)
        target.unlink(missing_ok=True)
    return _entry_payload(entry)


@router.post("/{key}/files")
async def add_folder_file(key: str, file: UploadFile = File(...)) -> dict:
    entry = _entry(key)
    if entry.kind != "file_folder":
        raise HTTPException(status_code=400, detail=f"{entry.label} manages a single file; use the file endpoint")
    filename = _safe_name(file.filename or "")
    _validate_extension(entry, filename)
    data = await _read_upload(file)
    if _storage() is not None:
        _register_remote(entry, filename, data)
        return _entry_payload(entry)
    folder = ROOT / entry.paths[0]
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / filename
    _backup(target, entry.key)
    target.write_bytes(data)
    return _entry_payload(entry)


@router.delete("/{key}/files/{filename}")
def delete_folder_file(key: str, filename: str) -> dict:
    entry = _entry(key)
    if entry.kind != "file_folder":
        raise HTTPException(status_code=400, detail=f"{entry.label} manages a single file; use the file endpoint")
    safe_filename = _safe_name(filename)
    if _storage() is not None:
        remote_names = {item["name"] for item in _remote_assets(entry.key)}
        if safe_filename not in remote_names:
            raise HTTPException(status_code=404, detail="File not found")
        _delete_remote(entry, safe_filename)
        return _entry_payload(entry)
    target = ROOT / entry.paths[0] / safe_filename
    if not target.exists():
        raise HTTPException(status_code=404, detail="File not found")
    _backup(target, entry.key)
    target.unlink()
    return _entry_payload(entry)
