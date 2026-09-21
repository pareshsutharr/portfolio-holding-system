"""Daily official NIFTY sector-allocation factsheet ingestion."""

from __future__ import annotations

import hashlib
import logging
import os
import re
import tempfile
import threading
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import pdfplumber
import requests
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

from market_etl.models import IndexSectorAllocation, IngestionRun

LOGGER = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]
EXPORT_DIR = ROOT / "data"
DOWNLOAD_ATTEMPTS = 3
RATE_LIMIT_SECONDS = 1.0
TOTAL_TOLERANCE = Decimal("0.25")
RUN_LOCK = threading.Lock()
ADVISORY_LOCK_NAME = "portfolio_analyzer_sector_allocations"


@dataclass(frozen=True)
class IndexSource:
    name: str
    label: str
    url: str
    filename: str
    export_name: str


SOURCES = {
    source.name: source
    for source in (
        IndexSource("NIFTY50", "NIFTY 50", "https://www.niftyindices.com/Factsheet/ind_nifty50.pdf", "ind_nifty50.pdf", "nifty50-sectors.txt"),
        IndexSource("NIFTYMIDCAP150", "NIFTY Midcap 150", "https://www.niftyindices.com/Factsheet/ind_Nifty_Midcap_150.pdf", "ind_Nifty_Midcap_150.pdf", "nifty-midcap150-sectors.txt"),
        IndexSource("NIFTY500", "NIFTY 500", "https://www.niftyindices.com/Factsheet/ind_nifty_500.pdf", "ind_nifty_500.pdf", "nifty500-sectors.txt"),
    )
}

DATE_PATTERN = re.compile(r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}\b")
ROW_PATTERN = re.compile(r"^(.+?)\s+(\d+(?:\.\d+)?)$")


def _collapse_doubled_glyphs(value: str) -> str:
    # Some NSE PDFs paint every visible glyph twice. Spaces are not duplicated,
    # so normalize repeated non-whitespace pairs rather than the entire string.
    return re.sub(r"([^\s])\1", r"\1", value.strip())


def extract_sector_representation(pdf_path: Path) -> tuple[date, list[tuple[str, Decimal]]]:
    """Extract only the left-column Sector Representation table and publication date."""
    with pdfplumber.open(pdf_path) as pdf:
        if not pdf.pages:
            raise ValueError("Factsheet has no pages")
        page = pdf.pages[0]
        full_text = page.extract_text() or ""
        first_line = full_text.splitlines()[0] if full_text else ""
        normalized_date_line = _collapse_doubled_glyphs(first_line)
        match = DATE_PATTERN.search(first_line) or DATE_PATTERN.search(normalized_date_line)
        if not match:
            raise ValueError("Factsheet publication date was not found")
        factsheet_date = datetime.strptime(match.group(0), "%B %d, %Y").date()

        left_text = page.crop((0, 0, page.width * 0.52, page.height)).extract_text() or ""
        marker = "Sector Representation"
        if marker not in left_text:
            raise ValueError("Sector Representation table was not found")
        block = left_text.split(marker, 1)[1]
        if "Sector Weight(%)" not in block:
            raise ValueError("Sector and Weight(%) columns were not found")
        block = block.split("Sector Weight(%)", 1)[1].split("## Based on", 1)[0]
        rows: list[tuple[str, Decimal]] = []
        for raw_line in block.splitlines():
            row_match = ROW_PATTERN.match(" ".join(raw_line.split()))
            if row_match:
                rows.append((row_match.group(1).strip(), Decimal(row_match.group(2))))
    validate_sector_rows(rows)
    return factsheet_date, rows


def validate_sector_rows(rows: list[tuple[str, Decimal]]) -> None:
    if not rows:
        raise ValueError("Sector Representation table is empty")
    names = [sector for sector, _ in rows]
    if any(not name.strip() for name in names):
        raise ValueError("Sector names cannot be empty")
    if len(set(names)) != len(names):
        raise ValueError("A sector is duplicated in the factsheet")
    if any(not weight.is_finite() or weight < 0 or weight > 100 for _, weight in rows):
        raise ValueError("Sector weights must be numeric percentages between 0 and 100")
    total = sum((weight for _, weight in rows), Decimal("0"))
    if abs(total - Decimal("100")) > TOTAL_TOLERANCE:
        raise ValueError(f"Sector weights total {total}%, expected approximately 100%")


def _playwright_download(source: IndexSource, destination: Path) -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Requests failed and Playwright fallback is not installed") from exc
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            response = browser.request.get(source.url, headers={"User-Agent": "Mozilla/5.0"}, timeout=60_000)
            if not response.ok:
                raise RuntimeError(f"Playwright download returned HTTP {response.status}")
            destination.write_bytes(response.body())
        finally:
            browser.close()


def download_factsheet(source: IndexSource, destination: Path) -> str:
    last_error: Exception | None = None
    for attempt in range(1, DOWNLOAD_ATTEMPTS + 1):
        try:
            response = requests.get(source.url, headers={"User-Agent": "Mozilla/5.0"}, timeout=45)
            response.raise_for_status()
            if not response.content.startswith(b"%PDF"):
                raise ValueError("Official URL did not return a PDF")
            destination.write_bytes(response.content)
            return "requests"
        except Exception as exc:
            last_error = exc
            LOGGER.warning("%s download attempt %s failed: %s", source.name, attempt, exc)
            if attempt < DOWNLOAD_ATTEMPTS:
                time.sleep(attempt * 2)
    LOGGER.info("Using Playwright fallback for %s", source.name)
    _playwright_download(source, destination)
    if not destination.read_bytes().startswith(b"%PDF"):
        raise ValueError("Playwright fallback did not return a PDF") from last_error
    return "playwright"


def _row_hash(index_name: str, sector: str, weight: Decimal, factsheet_date: date) -> str:
    value = f"{index_name}|{sector}|{weight.normalize()}|{factsheet_date.isoformat()}"
    return hashlib.sha256(value.encode()).hexdigest()


def classify_change(existing_hash: str | None, incoming_hash: str) -> str:
    if existing_hash is None:
        return "inserted"
    return "duplicate" if existing_hash == incoming_hash else "updated"


def _prepare_export(source: IndexSource, rows: list[tuple[str, Decimal]]) -> Path:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{source.export_name}.", dir=EXPORT_DIR)
    with os.fdopen(descriptor, "w", encoding="utf-8") as output:
        output.write("Sector Representation\nSector Weight(%)\n")
        for sector, weight in rows:
            output.write(f"{sector} {weight:.2f}\n")
        output.flush()
        os.fsync(output.fileno())
    os.chmod(temp_name, 0o644)
    return Path(temp_name)


def ingest_source(session_factory: sessionmaker[Session], source: IndexSource) -> dict:
    started = datetime.now(timezone.utc)
    with session_factory.begin() as session:
        run = IngestionRun(source=source.name, status="running", started_at=started)
        session.add(run)
        session.flush()
        run_id = run.id
    method = None
    temp_export: Path | None = None
    try:
        with tempfile.TemporaryDirectory(prefix="sector-factsheet-") as temp_dir:
            pdf_path = Path(temp_dir) / source.filename
            method = download_factsheet(source, pdf_path)
            factsheet_date, rows = extract_sector_representation(pdf_path)
            temp_export = _prepare_export(source, rows)
        inserted_count = updated_count = duplicate_count = 0
        with session_factory.begin() as session:
            existing = {
                row.sector: row
                for row in session.scalars(select(IndexSectorAllocation).where(
                    IndexSectorAllocation.index_name == source.name,
                    IndexSectorAllocation.factsheet_date == factsheet_date,
                ))
            }
            for sector, weight in rows:
                row_hash = _row_hash(source.name, sector, weight, factsheet_date)
                old = existing.get(sector)
                change = classify_change(old.row_hash if old else None, row_hash)
                if change == "inserted":
                    inserted_count += 1
                elif change == "duplicate":
                    duplicate_count += 1
                else:
                    updated_count += 1
                statement = insert(IndexSectorAllocation).values(
                    index_name=source.name, sector=sector, weight_percent=weight,
                    factsheet_date=factsheet_date, source_url=source.url,
                    source_file=source.filename, row_hash=row_hash,
                )
                session.execute(statement.on_conflict_do_update(
                    constraint="uq_index_sector_allocation_snapshot",
                    set_={"weight_percent": weight, "row_hash": row_hash, "source_url": source.url,
                          "source_file": source.filename, "updated_at": datetime.now(timezone.utc)},
                ))
            run = session.get(IngestionRun, run_id)
            run.status = "success"
            run.method_used = method
            run.records_fetched = len(rows)
            run.inserted = inserted_count
            run.updated = updated_count
            run.duplicates_skipped = duplicate_count
            run.finished_at = datetime.now(timezone.utc)
        os.replace(temp_export, EXPORT_DIR / source.export_name)
        temp_export = None
        return {"source": source.name, "status": "success", "factsheet_date": factsheet_date.isoformat(), "records_fetched": len(rows), "inserted": inserted_count, "updated": updated_count, "duplicates_skipped": duplicate_count}
    except Exception as exc:
        LOGGER.exception("Sector allocation ingestion failed for %s", source.name)
        with session_factory.begin() as session:
            run = session.get(IngestionRun, run_id)
            run.status = "failed"
            run.method_used = method
            run.finished_at = datetime.now(timezone.utc)
            run.error_message = str(exc)[:4000]
        return {"source": source.name, "status": "failed", "error": str(exc)}
    finally:
        if temp_export:
            temp_export.unlink(missing_ok=True)


def ingest_all(session_factory: sessionmaker[Session], *, wait_for_lock: bool = False) -> dict:
    acquired = RUN_LOCK.acquire(blocking=wait_for_lock)
    if not acquired:
        return {"status": "already_running", "results": []}
    engine = session_factory.kw["bind"]
    lock_connection = engine.connect()
    database_acquired = bool(lock_connection.scalar(text(
        "select pg_advisory_lock(hashtext(:name)) is null" if wait_for_lock
        else "select pg_try_advisory_lock(hashtext(:name))"
    ), {"name": ADVISORY_LOCK_NAME}))
    if wait_for_lock:
        database_acquired = True
    if not database_acquired:
        lock_connection.close()
        RUN_LOCK.release()
        return {"status": "already_running", "results": []}
    with session_factory.begin() as session:
        batch = IngestionRun(source="ALL_NIFTY_SECTORS", status="running")
        session.add(batch)
        session.flush()
        batch_id = batch.id
    try:
        results = []
        for position, source in enumerate(SOURCES.values()):
            if position:
                time.sleep(RATE_LIMIT_SECONDS)
            results.append(ingest_source(session_factory, source))
        successes = sum(item["status"] == "success" for item in results)
        status = "success" if successes == len(results) else "partial_success" if successes else "failed"
        with session_factory.begin() as session:
            batch = session.get(IngestionRun, batch_id)
            batch.status = status
            batch.method_used = "multi-source"
            batch.records_fetched = sum(item.get("records_fetched", 0) for item in results)
            batch.inserted = sum(item.get("inserted", 0) for item in results)
            batch.updated = sum(item.get("updated", 0) for item in results)
            batch.duplicates_skipped = sum(item.get("duplicates_skipped", 0) for item in results)
            batch.finished_at = datetime.now(timezone.utc)
            failures = [f"{item['source']}: {item.get('error', 'failed')}" for item in results if item["status"] == "failed"]
            batch.error_message = "; ".join(failures)[:4000] or None
        return {"status": status, "results": results}
    except Exception as exc:
        with session_factory.begin() as session:
            batch = session.get(IngestionRun, batch_id)
            batch.status = "failed"
            batch.finished_at = datetime.now(timezone.utc)
            batch.error_message = str(exc)[:4000]
        raise
    finally:
        lock_connection.execute(text("select pg_advisory_unlock(hashtext(:name))"), {"name": ADVISORY_LOCK_NAME})
        lock_connection.close()
        RUN_LOCK.release()


def is_ingestion_running() -> bool:
    return RUN_LOCK.locked()


def database_ingestion_running(session_factory: sessionmaker[Session]) -> bool:
    """Check the cross-process advisory lock without retaining it."""
    engine = session_factory.kw["bind"]
    with engine.connect() as connection:
        acquired = bool(connection.scalar(text("select pg_try_advisory_lock(hashtext(:name))"), {"name": ADVISORY_LOCK_NAME}))
        if acquired:
            connection.execute(text("select pg_advisory_unlock(hashtext(:name))"), {"name": ADVISORY_LOCK_NAME})
            return False
        return True
