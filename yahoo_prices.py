"""Refresh portfolio current market prices from Yahoo Finance."""

from __future__ import annotations

from datetime import date
from typing import Iterable

import pandas as pd
import yfinance as yf


# ETFs are not part of the SEBI equity market-cap master, so retain the small
# explicit ISIN-to-exchange-symbol lookup needed by the supported portfolio.
ISIN_TICKER_OVERRIDES = {
    "INF204KB17I5": "GOLDBEES.NS",
    "INF204KC1402": "SILVERBEES.NS",
}


def _symbol(value: object, suffix: str) -> str | None:
    cleaned = str(value or "").strip().upper()
    if not cleaned or cleaned in {"NAN", "-", "NONE"}:
        return None
    return cleaned if cleaned.endswith((".NS", ".BO")) else f"{cleaned}{suffix}"


def _latest_close(data: pd.DataFrame, ticker: str, ticker_count: int) -> float | None:
    try:
        if ticker_count == 1 and not isinstance(data.columns, pd.MultiIndex):
            close = data["Close"]
        else:
            close = data[ticker]["Close"]
        close = pd.to_numeric(close, errors="coerce").dropna()
        return round(float(close.iloc[-1]), 2) if not close.empty else None
    except (KeyError, IndexError, TypeError):
        return None


def _download(tickers: Iterable[str]) -> dict[str, float]:
    unique = list(dict.fromkeys(ticker for ticker in tickers if ticker))
    if not unique:
        return {}
    try:
        data = yf.download(
            unique,
            period="5d",
            interval="1d",
            auto_adjust=False,
            group_by="ticker",
            progress=False,
            threads=True,
        )
    except Exception:
        return {}
    return {
        ticker: price
        for ticker in unique
        if (price := _latest_close(data, ticker, len(unique))) is not None
    }


def add_yahoo_current_prices(portfolio: pd.DataFrame) -> pd.DataFrame:
    """Use NSE quotes first, BSE second, and workbook CMP only as a fallback."""
    result = portfolio.copy()
    result["isin"] = result["isin"].astype(str).str.strip().str.upper()

    primary = []
    fallback = []
    for row in result.itertuples():
        override = ISIN_TICKER_OVERRIDES.get(row.isin)
        primary.append(override or _symbol(getattr(row, "nse_symbol", ""), ".NS"))
        fallback.append(None if override else _symbol(getattr(row, "bse_symbol", ""), ".BO"))

    prices = _download([*primary, *fallback])
    yahoo_prices: list[float | None] = []
    used_tickers: list[str | None] = []
    for nse_ticker, bse_ticker in zip(primary, fallback):
        ticker = nse_ticker if nse_ticker in prices else bse_ticker
        yahoo_prices.append(prices.get(ticker) if ticker else None)
        used_tickers.append(ticker if ticker in prices else None)

    result["workbook_market_price"] = result["current_market_price"]
    result["yahoo_ticker"] = used_tickers
    result["yahoo_market_price"] = yahoo_prices
    has_yahoo_price = result["yahoo_market_price"].notna()
    result.loc[has_yahoo_price, "current_market_price"] = result.loc[
        has_yahoo_price, "yahoo_market_price"
    ]
    result["price_source"] = has_yahoo_price.map(
        {True: "Yahoo Finance", False: "Uploaded workbook"}
    )
    result["price_as_of"] = date.today().isoformat()
    result["closing_value"] = (
        result["quantity"] * result["current_market_price"]
    ).round(2)
    result["value"] = result["closing_value"]

    print("\n========== YAHOO FINANCE CMP ==========\n")
    print(f"Yahoo quotes   : {int(has_yahoo_price.sum())}")
    print(f"Workbook fallback: {int((~has_yahoo_price).sum())}")
    print(
        result[
            [
                "security_name",
                "yahoo_ticker",
                "current_market_price",
                "price_source",
            ]
        ].to_string(index=False)
    )
    return result
