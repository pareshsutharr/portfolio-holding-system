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
    ("5Y", pd.DateOffset(years=5)),
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
            "chart_series": {},
        }

        portfolio_path = portfolio_series.replace(0, np.nan).dropna()
        if len(portfolio_path) >= 2 and portfolio_path.iloc[0]:
            normalized = (portfolio_path / portfolio_path.iloc[0] - 1) * 100
            row["chart_series"]["Portfolio"] = [
                {"date": date.strftime("%Y-%m-%d"), "return": float(value)}
                for date, value in normalized.items()
            ]

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
            if has_full_history:
                benchmark_path = series.reindex(window_dates).ffill().bfill().dropna()
                if len(benchmark_path) >= 2 and benchmark_path.iloc[0]:
                    normalized = (benchmark_path / benchmark_path.iloc[0] - 1) * 100
                    row["chart_series"][name] = [
                        {"date": date.strftime("%Y-%m-%d"), "return": float(value)}
                        for date, value in normalized.items()
                    ]

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
        "total_equity_value": total_equity_value,
    }


def _series_stats(value_series: pd.Series) -> dict | None:
    """Annualised return, monthly-return distribution, and worst 3-day drop for a value path."""

    path = value_series.replace(0, np.nan).dropna()
    if len(path) < 2 or not path.iloc[0]:
        return None

    total_return = path.iloc[-1] / path.iloc[0] - 1
    elapsed_days = (path.index[-1] - path.index[0]).days
    annualized_return = (
        (1 + total_return) ** (365.25 / elapsed_days) - 1 if elapsed_days > 0 else np.nan
    )

    monthly = path.resample("ME").last()
    monthly_returns = monthly.pct_change().dropna()
    three_day_returns = path.pct_change(3).dropna()

    std_dev = float(monthly_returns.std()) if len(monthly_returns) >= 2 else np.nan
    annualized_std = std_dev * np.sqrt(12) if std_dev == std_dev else np.nan
    sharpe_ratio = (
        annualized_return / annualized_std
        if annualized_std and annualized_std == annualized_std
        else np.nan
    )

    return {
        "total_return_pct": float(total_return * 100),
        "annualized_return_pct": float(annualized_return * 100) if annualized_return == annualized_return else np.nan,
        "avg_monthly_return_pct": float(monthly_returns.mean() * 100) if len(monthly_returns) else np.nan,
        "best_month_pct": float(monthly_returns.max() * 100) if len(monthly_returns) else np.nan,
        "worst_month_pct": float(monthly_returns.min() * 100) if len(monthly_returns) else np.nan,
        "worst_3day_return_pct": float(three_day_returns.min() * 100) if len(three_day_returns) else np.nan,
        "std_dev_pct": float(std_dev * 100) if std_dev == std_dev else np.nan,
        "sharpe_ratio": float(sharpe_ratio) if sharpe_ratio == sharpe_ratio else np.nan,
        "pct_winning_months": float((monthly_returns > 0).mean() * 100) if len(monthly_returns) else np.nan,
        "pct_losing_months": float((monthly_returns <= 0).mean() * 100) if len(monthly_returns) else np.nan,
    }


def analyze_disparity(portfolio: pd.DataFrame) -> dict | None:
    """Since-inception portfolio vs. benchmark comparison: return disparity, the resulting
    opportunity loss in rupees, and a risk/return statistics table for each series.

    "Since inception" is approximated as the earliest date for which every currently-held
    equity stock has price history, since the analyzer has no record of when the client
    actually started investing -- only the current holdings and quantities.
    """

    prices = load_combined_price_history()
    benchmark_series = load_all_benchmark_series()

    sector = portfolio["sector"] if "sector" in portfolio else pd.Series("", index=portfolio.index)
    is_etf = portfolio["security_name"].combine(sector, _is_etf)
    equity = portfolio[~is_etf].copy()
    equity["isin"] = equity["isin"].astype(str).str.strip().str.upper()
    total_equity_value = float(equity["value"].sum())

    latest_date = prices.index.max()

    held_start_dates = []
    for _, holding in equity.iterrows():
        isin = holding["isin"]
        if isin not in prices.columns:
            continue
        series = prices[isin].dropna()
        if not series.empty:
            held_start_dates.append(series.index.min())

    if not held_start_dates:
        return None

    since_date = max(held_start_dates)
    if since_date >= latest_date:
        return None

    window_dates = prices.index[(prices.index >= since_date) & (prices.index <= latest_date)]
    portfolio_value_series = pd.Series(0.0, index=window_dates)
    covered_value_now = 0.0
    covered_value_then = 0.0

    for _, holding in equity.iterrows():
        isin = holding["isin"]
        if isin not in prices.columns:
            continue
        series = prices[isin].dropna()
        price_now = _asof(series, latest_date)
        price_then = _asof(series, since_date)
        if pd.isna(price_now) or pd.isna(price_then):
            continue

        qty = float(holding["quantity"])
        covered_value_now += qty * price_now
        covered_value_then += qty * price_then
        stock_window = series.reindex(window_dates).ffill()
        portfolio_value_series = portfolio_value_series.add(qty * stock_window, fill_value=0)

    if not covered_value_then:
        return None

    portfolio_return_pct = (covered_value_now / covered_value_then - 1) * 100
    invested_amount = total_equity_value

    series_stats: dict[str, dict] = {
        "Portfolio": {
            "return_pct": portfolio_return_pct,
            "stats": _series_stats(portfolio_value_series),
        }
    }

    for name, series in benchmark_series.items():
        has_full_history = series.index.min() <= since_date
        if not has_full_history:
            series_stats[name] = {"return_pct": np.nan, "stats": None}
            continue

        price_now = _asof(series, latest_date)
        price_then = _asof(series, since_date)
        if pd.isna(price_now) or pd.isna(price_then) or not price_then:
            series_stats[name] = {"return_pct": np.nan, "stats": None}
            continue

        bench_return_pct = (price_now / price_then - 1) * 100
        benchmark_window = series.reindex(window_dates).ffill().bfill()
        series_stats[name] = {
            "return_pct": bench_return_pct,
            "stats": _series_stats(benchmark_window),
        }

    opportunity_loss = {}
    for name in benchmark_series:
        bench_return_pct = series_stats[name]["return_pct"]
        if bench_return_pct != bench_return_pct:
            opportunity_loss[name] = {"disparity_pct": np.nan, "amount": np.nan}
            continue
        disparity_pct = portfolio_return_pct - bench_return_pct
        opportunity_loss[name] = {
            "disparity_pct": disparity_pct,
            "amount": invested_amount * (disparity_pct / 100),
        }

    return {
        "since_date": since_date,
        "as_of_date": latest_date,
        "invested_amount": invested_amount,
        "benchmark_names": list(benchmark_series.keys()),
        "series": series_stats,
        "opportunity_loss": opportunity_loss,
    }
