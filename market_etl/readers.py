"""Readers and normalizers for ACE Equity Excel exports."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

LOGGER = logging.getLogger(__name__)

DAILY_RENAME = {
    "Company Name": "company_name",
    "CD_ISIN No": "isin",
    "CD_Sector": "sector",
    "CD_Industry1": "industry",
    "NDP_Date": "trade_date",
    "NDP_Volume ('000)": "volume",
    "NDP_Mcap": "market_cap",
    "NDP_Close": "close_price",
    "NDP_Value": "turnover",
    "FR_Year": "financial_year",
    "FR_ROE (%)": "roe",
    "FR_ROCE (%)": "roce",
    "FR_Interest Cover(x)": "interest_cover",
    "FR_Total Debt/Equity(x)": "debt_equity",
}

HISTORICAL_REQUIRED = {
    "Company Name",
    "CD_ISIN No",
    "NDP_Date",
    "NDP_Volume ('000)",
    "NDP_Mcap",
    "NDP_Close",
    "NDP_Value",
}


def _find_header_row(path: Path, required_columns: set[str], scan_rows: int = 20) -> int:
    preview = pd.read_excel(path, header=None, nrows=scan_rows, dtype=object)
    for index, row in preview.iterrows():
        values = {str(value).strip() for value in row.dropna()}
        if required_columns.issubset(values):
            return int(index)
    raise ValueError(f"Could not find the expected ACE headers in {path}")


def _clean_common(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.rename(columns=lambda value: str(value).strip())
    frame = frame.rename(columns=DAILY_RENAME)
    frame = frame.replace(r"^\s*$", pd.NA, regex=True)
    if "isin" in frame:
        frame["isin"] = frame["isin"].astype("string").str.strip().str.upper()
    if "company_name" in frame:
        frame["company_name"] = frame["company_name"].astype("string").str.strip()
    if "trade_date" in frame:
        frame["trade_date"] = pd.to_datetime(frame["trade_date"], errors="coerce").dt.date
    numeric_columns = [
        "volume", "market_cap", "close_price", "turnover", "financial_year",
        "roe", "roce", "interest_cover", "debt_equity",
    ]
    for column in numeric_columns:
        if column in frame:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


def read_daily_ace(path: Path) -> pd.DataFrame:
    header_row = _find_header_row(path, set(DAILY_RENAME))
    frame = _clean_common(pd.read_excel(path, header=header_row))
    missing = set(DAILY_RENAME.values()) - set(frame.columns)
    if missing:
        raise ValueError(f"Daily ACE file is missing normalized fields: {sorted(missing)}")
    frame = frame.dropna(subset=["isin", "company_name"])
    LOGGER.info("Read %s valid rows from %s", len(frame), path)
    return frame


def read_historical_ace(path: Path) -> pd.DataFrame:
    header_row = _find_header_row(path, HISTORICAL_REQUIRED)
    frame = _clean_common(pd.read_excel(path, header=header_row))
    frame = frame.dropna(subset=["isin", "company_name", "trade_date"])
    LOGGER.info("Read %s valid historical rows from %s", len(frame), path)
    return frame

