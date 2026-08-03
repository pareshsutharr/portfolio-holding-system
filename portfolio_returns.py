"""Portfolio absolute-return and drawdown comparison against benchmarks.

Simulates holding the CURRENT portfolio (same ISINs, same quantities as
today) over the trailing 3-month, 6-month, 1-year and 3-year windows, and
compares the resulting absolute return and maximum drawdown against the
Nifty 50, Nifty Midcap 150 and Nifty 500 indices over the same windows.

Stock prices reuse the existing NSE-first / BSE-fallback daily price loader
(stock_style_market.load_combined_price_history). Benchmark prices come
from the root-level Data_Nifty_50.csv, Data_Nifty_150.csv and
Data_Nifty_500.csv files. Only equity holdings are considered; ETFs are
excluded.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

from stock_style_market import load_combined_price_history

PERIODS = [
    ("3M", pd.DateOffset(months=3)),
    ("6M", pd.DateOffset(months=6)),
    ("1Y", pd.DateOffset(years=1)),
    ("3Y", pd.DateOffset(years=3)),
]

BENCHMARK_FILES = {
    "Nifty 50": "Data_Nifty_50.csv",
    "Nifty Midcap 150": "Data_Nifty_150.csv",
    "Nifty 500": "Data_Nifty_500.csv",
}

_ETF_PATTERN = re.compile(
    r"\bETF\b|EXCHANGE TRADED|GOLD\s*BEES|NETF(?:GOLD|SILVER)", re.IGNORECASE
)


def _is_etf(security_name, sector) -> bool:
    label = f"{security_name or ''} {sector or ''}".upper()
    return bool(_ETF_PATTERN.search(label))


def load_benchmark_series(path: str) -> pd.Series:
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["Date"], format="%m/%d/%Y")
    df["close"] = (
        df["Price"].astype(str).str.replace(",", "", regex=False).astype(float)
    )
    series = df.set_index("date")["close"].sort_index()
    return series[~series.index.duplicated(keep="last")]


def load_all_benchmark_series() -> dict[str, pd.Series]:
    return {name: load_benchmark_series(path) for name, path in BENCHMARK_FILES.items()}


def _asof(series: pd.Series, target_date) -> float:
    valid = series.dropna()
    if valid.empty or target_date < valid.index.min():
        return np.nan
    return valid.asof(target_date)


def _max_drawdown(series: pd.Series, start_date, end_date) -> float:
    window = series[(series.index >= start_date) & (series.index <= end_date)].dropna()
    if len(window) < 2:
        return np.nan
    wealth = window / window.iloc[0]
    drawdown = wealth / wealth.cummax() - 1
    return abs(float(drawdown.min()))


def analyze_portfolio_returns(portfolio: pd.DataFrame) -> dict:
    prices = load_combined_price_history()
    benchmark_series = load_all_benchmark_series()

    sector = portfolio["sector"] if "sector" in portfolio else pd.Series("", index=portfolio.index)
    is_etf = portfolio["security_name"].combine(sector, _is_etf)
    equity = portfolio[~is_etf].copy()
    equity["isin"] = equity["isin"].astype(str).str.strip().str.upper()
    total_equity_value = float(equity["value"].sum())

    latest_date = prices.index.max()

    rows = []
    for label, offset in PERIODS:
        start_date = latest_date - offset

        window_dates = prices.index[
            (prices.index >= start_date) & (prices.index <= latest_date)
        ]
        portfolio_series = pd.Series(0.0, index=window_dates)

        covered_value_now = 0.0
        covered_value_then = 0.0
        covered_value_current = 0.0

        for _, holding in equity.iterrows():
            isin = holding["isin"]
            if isin not in prices.columns:
                continue
            series = prices[isin].dropna()
            price_now = _asof(series, latest_date)
            price_then = _asof(series, start_date)
            if pd.isna(price_now) or pd.isna(price_then):
                continue

            qty = float(holding["quantity"])
            covered_value_now += qty * price_now
            covered_value_then += qty * price_then
            covered_value_current += float(holding["value"])

            stock_window = series.reindex(window_dates).ffill()
            portfolio_series = portfolio_series.add(qty * stock_window, fill_value=0)

        portfolio_return = (
            covered_value_now / covered_value_then - 1 if covered_value_then else np.nan
        )
        portfolio_drawdown = (
            _max_drawdown(portfolio_series, start_date, latest_date)
            if covered_value_now else np.nan
        )
        coverage_percent = (
            covered_value_current / total_equity_value * 100 if total_equity_value else 0.0
        )

        row = {
            "period": label,
            "portfolio_return": portfolio_return,
            "portfolio_drawdown": portfolio_drawdown,
            "coverage_percent": coverage_percent,
        }

        for name, series in benchmark_series.items():
            price_now = _asof(series, latest_date)
            price_then = _asof(series, start_date)
            has_full_history = series.index.min() <= start_date
            if has_full_history and pd.notna(price_now) and pd.notna(price_then) and price_then:
                bench_return = price_now / price_then - 1
                bench_drawdown = _max_drawdown(series, start_date, latest_date)
            else:
                bench_return = np.nan
                bench_drawdown = np.nan
            row[f"{name}_return"] = bench_return
            row[f"{name}_drawdown"] = bench_drawdown

        rows.append(row)

    return {
        "as_of_date": latest_date,
        "rows": rows,
        "benchmark_names": list(benchmark_series.keys()),
        "benchmark_start_dates": {
            name: series.index.min() for name, series in benchmark_series.items()
        },
        "equity_holdings": int(len(equity)),
        "total_holdings": int(len(portfolio)),
    }
