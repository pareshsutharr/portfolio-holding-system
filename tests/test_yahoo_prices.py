import pandas as pd

import yahoo_prices


def test_yahoo_cmp_recalculates_value_and_tracks_source(monkeypatch):
    portfolio = pd.DataFrame(
        [
            {
                "security_name": "Example Ltd",
                "isin": "INE000A00001",
                "quantity": 10,
                "current_market_price": 90.0,
                "closing_value": 900.0,
                "value": 900.0,
                "nse_symbol": "EXAMPLE",
                "bse_symbol": "",
            },
            {
                "security_name": "No Quote Ltd",
                "isin": "INE000A00002",
                "quantity": 5,
                "current_market_price": 40.0,
                "closing_value": 200.0,
                "value": 200.0,
                "nse_symbol": "NOQUOTE",
                "bse_symbol": "",
            },
        ]
    )
    monkeypatch.setattr(
        yahoo_prices,
        "_download",
        lambda tickers: {"EXAMPLE.NS": 101.25},
    )

    result = yahoo_prices.add_yahoo_current_prices(portfolio)

    assert result.loc[0, "current_market_price"] == 101.25
    assert result.loc[0, "value"] == 1012.50
    assert result.loc[0, "price_source"] == "Yahoo Finance"
    assert result.loc[1, "current_market_price"] == 40.0
    assert result.loc[1, "value"] == 200.0
    assert result.loc[1, "price_source"] == "Uploaded workbook"
