from config import HOLDINGS_FILE

from header_detection import detect_header
from gemini_mapper import get_column_mapping
from holdings_parser import parse_holdings
from sector_industry import add_sector_industry
from market_cap import add_market_cap
from portfolio_analysis import analyze_portfolio

result = detect_header(HOLDINGS_FILE)

mapping = get_column_mapping(
    result["headers"]
)

portfolio = parse_holdings(
    result["dataframe"],
    result["header_row"],
    result["headers"],
    mapping
)

portfolio = add_sector_industry(
    portfolio
)

portfolio = add_market_cap(
    portfolio
)

analysis = analyze_portfolio(
    portfolio
)

print(analysis["summary"])