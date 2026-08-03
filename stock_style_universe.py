"""Loads the Accord Growth / Value / Quality / Liquidity workbooks into
per-ISIN raw metric tables used by the Stock Style Classification module.

Each workbook has 3 blank rows before the header, so header=3 (0-indexed).
The 6 yearly columns for a metric are named "<Metric>", "<Metric>1" ...
"<Metric>5", ordered most-recent-year first.
"""

import numpy as np
import pandas as pd

from config import (
    STYLE_GROWTH_FILE,
    STYLE_LIQUIDITY_FILE,
    STYLE_QUALITY_FILE,
    STYLE_VALUE_FILE,
)

ACCORD_HEADER_ROW = 3
ISIN_COLUMN = "CD_ISIN No"
NAME_COLUMN = "Company Name"


def _read_accord_sheet(path):
    df = pd.read_excel(path, header=ACCORD_HEADER_ROW)
    df[ISIN_COLUMN] = df[ISIN_COLUMN].astype(str).str.strip().str.upper()
    df = df.dropna(subset=[ISIN_COLUMN]).drop_duplicates(subset=[ISIN_COLUMN], keep="first")
    return df.set_index(ISIN_COLUMN)


def _year_columns(base, count):
    return [base] + [f"{base}{i}" for i in range(1, count)]


def _geometric_growth(df, base, years=5):
    """Compound `years` yearly growth-% columns (most-recent-first) into a
    single multi-year compounded growth rate, expressed as a fraction."""
    columns = _year_columns(base, years)
    values = df[columns].apply(pd.to_numeric, errors="coerce")
    factors = 1 + values / 100.0
    invalid = values.isna().any(axis=1) | (factors <= 0).any(axis=1)
    compounded = factors.prod(axis=1) ** (1 / years) - 1
    compounded[invalid] = np.nan
    return compounded


def _average_percent(df, base, years=5):
    columns = _year_columns(base, years)
    values = df[columns].apply(pd.to_numeric, errors="coerce")
    return values.mean(axis=1, skipna=False) / 100.0


def load_growth_universe():
    df = _read_accord_sheet(STYLE_GROWTH_FILE)

    result = pd.DataFrame(index=df.index)
    result["company_name"] = df[NAME_COLUMN]
    result["revenue_cagr5"] = _geometric_growth(df, "FR_Net Sales Growth(%)")
    result["pat_cagr5"] = _geometric_growth(df, "FR_PAT Growth(%)")
    result["eps_cagr5"] = _geometric_growth(df, "FR_Adj. EPS Growth(%)")
    result["roe_avg5"] = _average_percent(df, "FR_ROE (%)")
    result["roce_avg5"] = _average_percent(df, "FR_ROCE (%)")
    return result


def load_value_universe():
    df = _read_accord_sheet(STYLE_VALUE_FILE)

    def _clean_multiple(column):
        values = pd.to_numeric(df[column], errors="coerce")
        return values.where(values > 0)

    result = pd.DataFrame(index=df.index)
    result["company_name"] = df[NAME_COLUMN]
    result["pe"] = _clean_multiple("FR_Adjusted PE (x)")
    result["pb"] = _clean_multiple("FR_Price / Book Value(x)")
    result["ev_ebitda"] = _clean_multiple("FR_EV/EBITDA(x)")
    result["div_yield"] = pd.to_numeric(df["FR_Dividend Yield(%)"], errors="coerce") / 100.0
    return result


def load_quality_universe():
    df = _read_accord_sheet(STYLE_QUALITY_FILE)

    result = pd.DataFrame(index=df.index)
    result["company_name"] = df[NAME_COLUMN]
    result["roe_latest"] = pd.to_numeric(df["FR_ROE (%)"], errors="coerce") / 100.0
    result["roce_latest"] = pd.to_numeric(df["FR_ROCE (%)"], errors="coerce") / 100.0
    result["debt_equity_latest"] = pd.to_numeric(df["FR_Total Debt/Equity(x)"], errors="coerce")
    result["interest_cover_latest"] = pd.to_numeric(df["FR_Interest Cover(x)"], errors="coerce")
    return result


def load_liquidity_universe():
    df = _read_accord_sheet(STYLE_LIQUIDITY_FILE)

    bse_volume = pd.to_numeric(df["DQRYAvg Volume(000) BSE"], errors="coerce")
    nse_volume = pd.to_numeric(df["DQRYAvg Volume  (000) NSE"], errors="coerce")
    bse_value = pd.to_numeric(df["DQRYAvg Value BSE"], errors="coerce")
    nse_value = pd.to_numeric(df["DQRYAvg Value NSE"], errors="coerce")

    result = pd.DataFrame(index=df.index)
    result["company_name"] = df[NAME_COLUMN]
    result["adv"] = _combine_optional(bse_volume, nse_volume)
    result["adt"] = _combine_optional(bse_value, nse_value)
    return result


def _combine_optional(a, b):
    both_missing = a.isna() & b.isna()
    combined = a.fillna(0) + b.fillna(0)
    combined[both_missing] = np.nan
    return combined
