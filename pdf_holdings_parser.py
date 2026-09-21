"""Extract the Equity Holdings table from a portfolio-statement PDF (the
"Serial No. / Name / No. Of Shares / ... / Current Value (Rs.)" layout produced
by RM/broker statement exports) into the same raw shape parse_holdings()
expects: one row per holding with security_name, quantity, and value.

ISIN is not present in this statement format, so it is resolved separately
via company_isin_matcher.resolve_company_isins() once the table is extracted.
"""

from __future__ import annotations

import re

import pandas as pd
import pdfplumber

from company_isin_matcher import resolve_company_isins

_NON_HOLDING_NAMES = {"payout", "total", ""}


def _normalize_header(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").replace("\n", " ").lower()).strip()


def _find_column(headers: list[str], *, all_of: tuple[str, ...] = (), none_of: tuple[str, ...] = ()) -> int | None:
    for index, header in enumerate(headers):
        if all(token in header for token in all_of) and not any(token in header for token in none_of):
            return index
    return None


def _is_holdings_header(headers: list[str]) -> bool:
    return (
        _find_column(headers, all_of=("serial", "no")) is not None
        and "name" in headers
        and _find_column(headers, all_of=("shares",)) is not None
        and _find_column(headers, all_of=("current", "value"), none_of=("average",)) is not None
    )


def _to_numeric(value: object) -> float | None:
    text = str(value or "").strip().replace("₹", "").replace(",", "")
    if not text:
        return None
    negative = text.startswith("(") and text.endswith(")")
    text = text.strip("()")
    try:
        number = float(text)
    except ValueError:
        return None
    return -number if negative else number


def parse_pdf_holdings(pdf_path) -> pd.DataFrame:
    """Return raw holdings (security_name, quantity, current_market_price, value)
    extracted from a portfolio-statement PDF's Equity Holdings table."""

    rows: list[list[str]] = []
    column_count: int | None = None
    name_idx = shares_idx = price_idx = value_idx = None

    with pdfplumber.open(pdf_path) as pdf:
        holdings_table_found = False
        for page in pdf.pages:
            for table in page.extract_tables():
                if not table:
                    continue

                if not holdings_table_found:
                    header_row = [_normalize_header(cell) for cell in table[0]]
                    if not _is_holdings_header(header_row):
                        continue
                    holdings_table_found = True
                    column_count = len(table[0])
                    name_idx = header_row.index("name")
                    shares_idx = _find_column(header_row, all_of=("shares",))
                    price_idx = _find_column(header_row, all_of=("market", "price"))
                    value_idx = _find_column(header_row, all_of=("current", "value"), none_of=("average",))
                    rows.extend(table[1:])
                    continue

                # A continuation table on a later page: same column count, no header.
                if len(table[0]) == column_count:
                    rows.extend(table)

    if not holdings_table_found or name_idx is None or shares_idx is None or value_idx is None:
        raise ValueError("Could not find an Equity Holdings table in this PDF")

    records = []
    for row in rows:
        serial = str(row[0] or "").strip()
        name = str(row[name_idx] or "").strip()
        if not re.fullmatch(r"\d+", serial) or name.lower() in _NON_HOLDING_NAMES:
            continue

        quantity = _to_numeric(row[shares_idx])
        value = _to_numeric(row[value_idx])
        price = _to_numeric(row[price_idx]) if price_idx is not None else None
        if quantity is None or value is None:
            continue

        records.append({
            "security_name": name,
            "quantity": quantity,
            "closing_value": value,
            "current_market_price": price if price is not None else round(value / quantity, 2),
        })

    if not records:
        raise ValueError("Equity Holdings table in this PDF has no parseable rows")

    return pd.DataFrame.from_records(records)


def parse_pdf_portfolio(pdf_path) -> tuple[pd.DataFrame, list[str]]:
    """Extract holdings from a portfolio-statement PDF and resolve each company
    name to an ISIN, producing the same standardized schema parse_holdings()
    returns for Excel uploads (security_name, isin, quantity, closing_value,
    current_market_price, value). Returns (standard_df, unresolved_names) --
    any holding whose name couldn't be matched to a listed company is dropped
    and reported back so the caller can warn about it rather than silently
    under-counting the portfolio.
    """

    raw = parse_pdf_holdings(pdf_path)
    resolved = resolve_company_isins(raw["security_name"].tolist())

    raw = raw.copy()
    raw["isin"] = raw["security_name"].map(
        lambda name: (resolved.get(name) or {}).get("isin")
    )
    unresolved_names = [name for name in raw["security_name"] if not resolved.get(name)]

    standard_df = raw[raw["isin"].notna() & (raw["isin"] != "")].copy()
    standard_df = standard_df.drop_duplicates(subset="isin").reset_index(drop=True)
    standard_df["value"] = standard_df["closing_value"]

    return (
        standard_df[["security_name", "isin", "quantity", "closing_value", "current_market_price", "value"]],
        unresolved_names,
    )
