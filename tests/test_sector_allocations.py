from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas

from api.main import app
from market_etl.sector_allocations import (
    _row_hash,
    classify_change,
    extract_sector_representation,
    validate_sector_rows,
)


def _factsheet(path: Path) -> None:
    document = canvas.Canvas(str(path), pagesize=(595, 842))
    document.drawString(40, 810, "July 31, 2026")
    document.drawString(40, 600, "Sector Representation")
    document.drawString(40, 580, "Sector Weight(%)")
    document.drawString(40, 560, "Financial Services 60.00")
    document.drawString(40, 540, "Information Technology 40.00")
    document.drawString(40, 520, "## Based on Price Return Index.")
    document.drawString(330, 560, "Portfolio Characteristics 999.00")
    document.save()


def test_extracts_only_sector_representation_and_publication_date(tmp_path: Path) -> None:
    path = tmp_path / "factsheet.pdf"
    _factsheet(path)
    factsheet_date, rows = extract_sector_representation(path)
    assert factsheet_date == date(2026, 7, 31)
    assert rows == [("Financial Services", Decimal("60.00")), ("Information Technology", Decimal("40.00"))]


def test_validation_rejects_duplicates_and_invalid_total() -> None:
    with pytest.raises(ValueError, match="duplicated"):
        validate_sector_rows([("Financial Services", Decimal("50")), ("Financial Services", Decimal("50"))])
    with pytest.raises(ValueError, match="approximately 100"):
        validate_sector_rows([("Financial Services", Decimal("90"))])


def test_duplicate_detection_uses_stable_row_hash() -> None:
    original = _row_hash("NIFTY50", "Financial Services", Decimal("36.18"), date(2026, 7, 31))
    assert classify_change(None, original) == "inserted"
    assert classify_change(original, original) == "duplicate"
    changed = _row_hash("NIFTY50", "Financial Services", Decimal("36.19"), date(2026, 7, 31))
    assert classify_change(original, changed) == "updated"


def test_admin_sector_api_requires_authentication() -> None:
    response = TestClient(app).get("/api/admin/sector-allocations/status")
    assert response.status_code == 401
