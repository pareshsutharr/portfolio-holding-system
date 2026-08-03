from pathlib import Path

from market_etl.readers import read_daily_ace, read_historical_ace


ROOT = Path(__file__).resolve().parents[1]


def test_daily_reader_detects_plugin_title_row() -> None:
    frame = read_daily_ace(ROOT / "Daily_Data.xlsx")
    assert not frame.empty
    assert {"isin", "sector", "financial_year", "trade_date"}.issubset(frame.columns)
    assert frame["isin"].str.startswith("IN").any()


def test_historical_reader_detects_leading_blank_rows() -> None:
    candidates = sorted((ROOT / "Data").glob("*.xlsx"))
    assert candidates
    frame = read_historical_ace(candidates[0])
    assert not frame.empty
    assert {"isin", "trade_date", "close_price"}.issubset(frame.columns)
