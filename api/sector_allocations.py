"""Administrator API for NIFTY sector-allocation snapshots and ingestion status."""

from __future__ import annotations

from datetime import date
from threading import Lock

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from sqlalchemy import desc, func, select

from market_etl.config import Settings
from market_etl.database import build_engine, build_session_factory
from market_etl.models import IndexSectorAllocation, IngestionRun
from market_etl.sector_allocations import SOURCES, database_ingestion_running, ingest_all, is_ingestion_running

router = APIRouter(prefix="/api/admin/sector-allocations", tags=["sector-allocations"])
SESSIONS = build_session_factory(build_engine(Settings.from_env().database_url))
QUEUE_LOCK = Lock()
queued = False


def _allocation_payload(row: IndexSectorAllocation) -> dict:
    return {
        "id": row.id,
        "index_name": row.index_name,
        "sector": row.sector,
        "weight_percent": float(row.weight_percent),
        "factsheet_date": row.factsheet_date,
        "source_url": row.source_url,
        "source_file": row.source_file,
        "ingested_at": row.ingested_at,
        "updated_at": row.updated_at,
    }


@router.get("")
def list_allocations(
    index_name: str = Query("NIFTY50", alias="indexName"),
    factsheet_date: date | None = Query(None, alias="factsheetDate"),
    latest: bool = True,
) -> dict:
    if index_name not in SOURCES:
        raise HTTPException(status_code=422, detail="Unsupported indexName")
    with SESSIONS() as session:
        selected_date = factsheet_date
        if selected_date is None and latest:
            selected_date = session.scalar(select(func.max(IndexSectorAllocation.factsheet_date)).where(IndexSectorAllocation.index_name == index_name))
        statement = select(IndexSectorAllocation).where(IndexSectorAllocation.index_name == index_name)
        if selected_date is not None:
            statement = statement.where(IndexSectorAllocation.factsheet_date == selected_date)
        rows = session.scalars(statement.order_by(desc(IndexSectorAllocation.weight_percent))).all()
    return {"index_name": index_name, "factsheet_date": selected_date, "allocations": [_allocation_payload(row) for row in rows]}


@router.get("/history")
def allocation_history(index_name: str = Query("NIFTY50", alias="indexName")) -> dict:
    if index_name not in SOURCES:
        raise HTTPException(status_code=422, detail="Unsupported indexName")
    with SESSIONS() as session:
        rows = session.scalars(select(IndexSectorAllocation).where(IndexSectorAllocation.index_name == index_name).order_by(desc(IndexSectorAllocation.factsheet_date), desc(IndexSectorAllocation.weight_percent))).all()
    dates = sorted({row.factsheet_date for row in rows}, reverse=True)
    snapshots: dict[str, list[dict]] = {}
    for row in rows:
        snapshots.setdefault(row.factsheet_date.isoformat(), []).append(_allocation_payload(row))
    return {"index_name": index_name, "dates": dates, "snapshots": snapshots}


@router.get("/status")
def ingestion_status() -> dict:
    with SESSIONS() as session:
        latest_dates = dict(session.execute(select(IndexSectorAllocation.index_name, func.max(IndexSectorAllocation.factsheet_date)).group_by(IndexSectorAllocation.index_name)).all())
        runs = session.scalars(select(IngestionRun).order_by(desc(IngestionRun.started_at)).limit(30)).all()
        latest_batch = session.scalar(select(IngestionRun).where(IngestionRun.source == "ALL_NIFTY_SECTORS").order_by(desc(IngestionRun.started_at)).limit(1))
        last_success = session.scalar(select(func.max(IngestionRun.finished_at)).where(IngestionRun.source == "ALL_NIFTY_SECTORS", IngestionRun.status == "success"))
    return {
        "running": is_ingestion_running() or queued or database_ingestion_running(SESSIONS),
        "latest_dates": {name: latest_dates.get(name) for name in SOURCES},
        "last_successful_ingestion": last_success,
        "latest_status": latest_batch.status if latest_batch else "never_run",
        "runs": [{
            "id": run.id, "source": run.source, "status": run.status,
            "method_used": run.method_used, "records_fetched": run.records_fetched,
            "inserted": run.inserted, "updated": run.updated,
            "duplicates_skipped": run.duplicates_skipped, "started_at": run.started_at,
            "finished_at": run.finished_at, "error_message": run.error_message,
        } for run in runs],
    }


def _background_refresh() -> None:
    global queued
    try:
        ingest_all(SESSIONS)
    finally:
        with QUEUE_LOCK:
            queued = False


@router.post("/refresh", status_code=status.HTTP_202_ACCEPTED)
def refresh_allocations(background_tasks: BackgroundTasks) -> dict:
    global queued
    with QUEUE_LOCK:
        if queued or is_ingestion_running() or database_ingestion_running(SESSIONS):
            raise HTTPException(status_code=409, detail="A sector-data refresh is already running")
        queued = True
    background_tasks.add_task(_background_refresh)
    return {"status": "queued", "message": "All three official factsheets will be refreshed in the background"}
