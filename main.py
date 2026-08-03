import os
import sys
import warnings
from pathlib import Path


# Always use the project's managed environment, even when this file is started
# with macOS's system `python3`.
PROJECT_ROOT = Path(__file__).resolve().parent
VENV_PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python"
if VENV_PYTHON.exists() and Path(sys.prefix).resolve() != (PROJECT_ROOT / ".venv").resolve():
    print(f"Switching to project Python: {VENV_PYTHON}", flush=True)
    os.execv(str(VENV_PYTHON), [str(VENV_PYTHON), *sys.argv])

# Some vendor workbooks omit an optional default style. OpenPyXL safely applies
# its own default, so keep that non-actionable warning out of normal CLI output.
warnings.filterwarnings(
    "ignore",
    message="Workbook contains no default style, apply openpyxl's default",
    category=UserWarning,
    module=r"openpyxl\.styles\.stylesheet",
)

from header_detection import detect_header
from gemini_mapper import get_column_mapping
from holdings_parser import parse_holdings
from sector_industry import add_sector_industry
from sector_mapping import apply_sector_mapping
from market_cap import add_market_cap
from yahoo_prices import add_yahoo_current_prices
from portfolio_analysis import analyze_portfolio
from charts import generate_all_charts
from pdf_reports import PortfolioPDF
from benchmark_analysis import analyze_all_benchmarks
from benchmark_charts import generate_benchmark_charts
from benchmark_reader import load_all_benchmarks
from market_etl.config import Settings
from market_etl.database import build_engine, build_session_factory
from market_etl.services import BenchmarkService, DailyUpdateService
from riskometer import Riskometer
from stock_style import StockStyleClassifier
from portfolio_returns import analyze_portfolio_returns

from config import HOLDINGS_FILE, STYLE_CONFIG_FILE


# =====================================
# STEP 0 : REFRESH DATABASE
# =====================================

settings = Settings.from_env()
engine = build_engine(settings.database_url)
DailyUpdateService(
    build_session_factory(engine),
    BenchmarkService(settings.benchmark_symbol, settings.benchmark_name),
).run(settings.daily_ace_file)


# =====================================
# STEP 1 : HEADER DETECTION
# =====================================

result = detect_header(HOLDINGS_FILE)


# =====================================
# STEP 2 : COLUMN MAPPING
# =====================================

mapping = get_column_mapping(
    result["headers"]
)


# =====================================
# STEP 3 : PARSE HOLDINGS
# =====================================

portfolio = parse_holdings(
    result["dataframe"],
    result["header_row"],
    result["headers"],
    mapping
)


# =====================================
# STEP 4 : ADD SECTOR & INDUSTRY
# =====================================

portfolio = add_sector_industry(
    portfolio
)


# =====================================
# STEP 5 : MAP ACE SECTORS TO NSE SECTORS
# =====================================

portfolio = apply_sector_mapping(
    portfolio
)


# =====================================
# STEP 6 : ADD MARKET CAP
# =====================================

portfolio = add_market_cap(
    portfolio
)

# =====================================
# STEP 6A : REFRESH CMP FROM YAHOO
# =====================================

portfolio = add_yahoo_current_prices(portfolio)


# =====================================
# STEP 7 : PORTFOLIO ANALYSIS
# =====================================

analysis = analyze_portfolio(
    portfolio
)

# =====================================
# STEP 7A : RISK-O-METER
# =====================================

risk_analysis = Riskometer(
    engine,
    Path("riskometer_config.json")
).analyze(portfolio)


# =====================================
# STEP 7B : STOCK STYLE CLASSIFICATION
# =====================================

style_analysis = StockStyleClassifier(
    Path(STYLE_CONFIG_FILE)
).analyze(portfolio)

# =====================================
# STEP 7C : PORTFOLIO RETURNS VS BENCHMARKS
# =====================================

returns_analysis = analyze_portfolio_returns(
    portfolio
)


# =====================================
# STEP 8 : BENCHMARK ANALYSIS
# =====================================

all_benchmark_data = load_all_benchmarks()

analysis = analyze_all_benchmarks(
    analysis,
    all_benchmark_data
)


# =====================================
# STEP 9 : GENERATE CHARTS
# =====================================

chart_paths = generate_all_charts(
    analysis
)

benchmark_chart_paths = generate_benchmark_charts(
    analysis
)

chart_paths.update(
    benchmark_chart_paths
)


# =====================================
# STEP 10 : GENERATE PDF
# =====================================

pdf = PortfolioPDF(
    analysis=analysis,
    chart_paths=chart_paths,
    risk_analysis=risk_analysis,
    style_analysis=style_analysis,
    returns_analysis=returns_analysis
)

pdf.generate()


# =====================================
# FINAL OUTPUT
# =====================================

print("\n========== ANALYSIS COMPLETE ==========\n")

print(analysis["summary"])

print("\n========== RISK-O-METER ==========\n")

print(
    f"Overall Portfolio Risk : "
    f"{risk_analysis['overall_score']:.2f} "
    f"({risk_analysis['overall_level']})"
)

for result in risk_analysis["results"]:
    print(
        f"{result.name.replace('_', ' ').title()} : "
        f"{result.score:.2f} ({result.level}) "
        f"- Coverage: {result.coverage}"
    )

print("\n========== GENERATED CHARTS ==========\n")

for name, path in chart_paths.items():
    print(f"{name} : {path}")

print("\nPortfolio Analysis Completed Successfully.")
