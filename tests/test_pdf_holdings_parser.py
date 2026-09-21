from company_isin_matcher import _normalize
from pdf_holdings_parser import _is_holdings_header, _normalize_header, _to_numeric


def test_normalize_header_collapses_multiline_and_punctuation() -> None:
    assert _normalize_header("Current\nMarket\nPrice (Rs.)") == "current market price rs"
    assert _normalize_header("Serial No.") == "serial no"
    assert _normalize_header("Current Value\n(Rs.)") == "current value rs"


def test_is_holdings_header_matches_the_equity_holdings_table() -> None:
    headers = [
        "serial no", "name", "no of shares", "average cost rs", "average buy value rs",
        "current market price rs", "current value rs", "gain loss rs", "return", "holding",
    ]
    assert _is_holdings_header(headers)


def test_is_holdings_header_rejects_unrelated_tables() -> None:
    assert not _is_holdings_header(["description", "asset class", "no of units", "current value"])
    assert not _is_holdings_header(["since inception", "rom"])


def test_to_numeric_handles_indian_grouping_and_parens_for_negatives() -> None:
    assert _to_numeric("3,03,380.00") == 303380.0
    assert _to_numeric("(8.62)") == -8.62
    assert _to_numeric("") is None
    assert _to_numeric(None) is None


def test_normalize_strips_legal_suffixes_and_punctuation_for_matching() -> None:
    assert _normalize("Britannia Industires Ltd.") == "britannia industires"
    assert _normalize("Reliance Industires Limited") == "reliance industires"
    assert _normalize("State Bank of India") == "state bank of india"
