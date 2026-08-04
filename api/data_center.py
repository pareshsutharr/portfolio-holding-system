"""Admin data-management API: list, upload, replace, and delete the raw
reference/master files the analysis pipeline reads from disk.

Every managed path below is grounded in config.py / portfolio_returns.py --
this does not invent new locations. Destructive operations always back the
previous file up under runtime/data-center-backups/ first, so nothing is
unrecoverably lost through the UI.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

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
    if entry.kind == "single_file":
        primary = ROOT / entry.paths[0]
        payload["file"] = _file_info(primary)
        payload["synced_paths"] = list(entry.paths) if len(entry.paths) > 1 else []
    else:
        folder = ROOT / entry.paths[0]
        files = _folder_files(folder)
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
    target = ROOT / entry.paths[0] / safe_filename
    if not target.exists():
        raise HTTPException(status_code=404, detail="File not found")
    _backup(target, entry.key)
    target.unlink()
    return _entry_payload(entry)
