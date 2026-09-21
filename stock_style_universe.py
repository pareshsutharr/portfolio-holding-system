"""Loads the Accord master workbook (Growth / Value / Quality / Liquidity raw
inputs) into per-ISIN raw metric tables used by the Stock Style
Classification module. Quality's Debt/Equity ratio is not in the master
export, so it's still read from the legacy Data_Quality.xlsx workbook.

Each workbook has 3 blank rows before the header, so header=3 (0-indexed).
The 5 yearly columns for a metric are named "<Metric>", "<Metric>1" ...
"<Metric>4", ordered most-recent-year first.
"""

import numpy as np
import pandas as pd

from config import STYLE_ACCORD_MASTER_FILE, STYLE_QUALITY_FILE

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


def _true_cagr(df, base, years=4):
    """CAGR from `years + 1` raw yearly level columns (most-recent-first):
    (latest / oldest) ** (1 / years) - 1. N/A whenever any year in the
    window is missing, zero, or negative."""
    columns = _year_columns(base, years + 1)
    values = df[columns].apply(pd.to_numeric, errors="coerce")
    invalid = values.isna().any(axis=1) | (values <= 0).any(axis=1)
    latest, oldest = values[columns[0]], values[columns[-1]]
    cagr = (latest / oldest) ** (1 / years) - 1
    cagr[invalid] = np.nan
    return cagr


def _average_percent(df, base, years=5):
    columns = _year_columns(base, years)
    values = df[columns].apply(pd.to_numeric, errors="coerce")
    return values.mean(axis=1, skipna=False) / 100.0


def load_growth_universe():
    df = _read_accord_sheet(STYLE_ACCORD_MASTER_FILE)

    result = pd.DataFrame(index=df.index)
    result["company_name"] = df[NAME_COLUMN]
    result["revenue_cagr5"] = _true_cagr(df, "YR_Net Sales")
    result["pat_cagr5"] = _true_cagr(df, "FH_PAT")
    result["eps_cagr5"] = _true_cagr(df, "YR_Adj Calculated EPS Annualised (Unit.Curr.)")
    result["roe_avg5"] = _average_percent(df, "FR_ROE (%)")
    result["roce_avg5"] = _average_percent(df, "FR_ROCE (%)")
    return result


def load_value_universe():
    df = _read_accord_sheet(STYLE_ACCORD_MASTER_FILE)

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
    df = _read_accord_sheet(STYLE_ACCORD_MASTER_FILE)
    # Debt/Equity isn't in the Accord master export; keep sourcing it from
    # the legacy workbook until that column is added upstream.
    legacy = _read_accord_sheet(STYLE_QUALITY_FILE)
    debt_equity = pd.to_numeric(legacy["FR_Total Debt/Equity(x)"], errors="coerce")

    result = pd.DataFrame(index=df.index)
    result["company_name"] = df[NAME_COLUMN]
    result["roe_latest"] = pd.to_numeric(df["FR_ROE (%)"], errors="coerce") / 100.0
    result["roce_latest"] = pd.to_numeric(df["FR_ROCE (%)"], errors="coerce") / 100.0
    result["debt_equity_latest"] = debt_equity.reindex(result.index)
    result["interest_cover_latest"] = pd.to_numeric(df["FR_Interest Cover(x)"], errors="coerce")
    return result


def load_liquidity_universe():
    df = _read_accord_sheet(STYLE_ACCORD_MASTER_FILE)

    result = pd.DataFrame(index=df.index)
    result["company_name"] = df[NAME_COLUMN]
    result["adv"] = pd.to_numeric(df["DQRY_Avg Volume  ('000)"], errors="coerce")
    result["adt"] = pd.to_numeric(df["DQRY_Avg Value"], errors="coerce")
    return result
