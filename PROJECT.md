# Portfolio Analyzer — Project Overview

## What this project is

A tool that takes a client's stock holdings (an Excel export from a broker) and turns them
into a polished PDF report: sector/industry/market-cap breakdown vs. NIFTY benchmarks, a
**Risk-O-Meter** score, a **Stock Style** (Growth/Value/Momentum/Quality) classification, and
returns vs. benchmark comparisons.

Alongside that, there's a PostgreSQL database (`market_data`) that stores daily NSE/BSE
market data and company fundamentals, fed from a data vendor's ("ACE Equity" / Accord) Excel
exports. The Risk-O-Meter reads from this database live; everything else still reads flat
Excel/CSV files directly.

**In short: one pipeline, two data-access styles, currently in the middle of migrating from
"read Excel files" to "read Postgres."** See [Two systems](#two-systems-excel-vs-postgres) below.

---

## How a normal run works (`main.py`)

There's no CLI — you just run `python main.py`, and it reads fixed file paths from
`config.py`. It's a straight-line pipeline:

1. **Refresh the database** — loads the latest `Daily_Data.xlsx` into Postgres and pulls
   fresh NIFTY 50 closes from Yahoo Finance.
2. **Detect the header row** in the client's holdings Excel file (`header_detection.py`) —
   broker exports have a variable number of title rows before the real data starts.
3. **Map columns with Gemini** (`gemini_mapper.py`) — every broker labels its columns
   differently, so an LLM call maps whatever headers exist onto four standard fields:
   `security_name`, `isin`, `quantity`, `closing_value`.
4. **Parse holdings** (`holdings_parser.py`) into a clean, standardized table.
5. **Enrich with sector/industry** from ACE's own master data, then **remap ACE's sector
   names to NSE's sector taxonomy** (`sector_mapping.json`).
6. **Add market-cap category** (Large/Mid/Small/Micro, per SEBI classification).
7. **Portfolio analysis** — weights, sector/industry/cap allocation, concentration metrics.
8. **Risk-O-Meter** — a 0–100 risk score (reads live from Postgres).
9. **Stock Style classification** — Growth/Value/Momentum/Quality tags per holding (reads
   from Excel files only).
10. **Returns vs. benchmarks** — portfolio performance vs. NIFTY 50/150/500 over various
    windows.
11. **Benchmark comparison** — sector mix and top holdings vs. the NIFTY indices.
12. **Charts** — donuts/bars saved as PNGs to `output/`.
13. **PDF assembly** (`pdf_reports.py`) — everything above becomes `output/portfolio_report.pdf`.

`main_industry.py` is an **earlier, monolithic version** of this same idea (1,100+ lines,
one big script, its own duplicate chart/PDF code). It's the "before" snapshot of the refactor
that produced `main.py` and all the small modules — it still works, but it's not what you
should run day to day.

---

## Two systems: Excel vs. Postgres

There are genuinely two parallel ways this project reads data, and they meet in exactly one
place.

**File-based (the original approach)** — used by holdings parsing, sector/market-cap
enrichment, Stock Style classification, portfolio returns, and benchmark comparisons. All of
these read directly from Excel/CSV files in `test_files/`, the root `Data_*` files, and
`Portfolio Analyzer Data/`.

**Postgres-backed (`market_etl/` + `scripts/`)** — built so that "later risk calculations can
consume the database without coupling themselves to Excel" (see `DATABASE_ETL.md`). It ingests
the same ACE Excel exports into proper database tables.

**The Risk-O-Meter is the one place they connect.** `main.py` builds a single database
connection and hands it to `Riskometer`, which runs live queries against the database for
company data, fundamentals, and daily prices — but it *still* falls back to one Excel file
(`test_files/MCap.xlsx`) for market-cap category, and to flat CSVs for benchmark index series.
So even the "migrated" module is a hybrid, not fully cut over.

**Stock Style classification, portfolio returns, and benchmark comparisons never touch
Postgres** — they read the same kind of data (prices, fundamentals) but from a completely
separate set of Excel files. This means the same underlying information is effectively
duplicated across two pipelines that don't talk to each other yet.

---

## The Risk-O-Meter (`riskometer.py`)

Produces a single 0–100 portfolio risk score (Very Low → Very High), built from seven
weighted sub-scores, each reported individually with its own explanation:

| Sub-score | What it measures |
|---|---|
| Concentration | Largest holding / top-3 / top-5 weight, Herfindahl index |
| Sector | Largest sector weight, sector HHI, number of sectors |
| Market cap | Weighted risk by Large/Mid/Small/Micro cap bucket |
| Quality | ROE, ROCE, Debt/Equity, Interest Cover (ETFs excluded; Interest Cover waived for banks/NBFCs) |
| Liquidity | 63-day average volume/turnover vs. cap-tier-specific bands |
| Volatility | Annualized volatility, max drawdown, downside volatility (up to 252 trading days) |
| Beta | Stock vs. its cap-appropriate benchmark (Nifty 50 / Midcap 150 / Nifty 500) |

Config lives in `riskometer_config.json` (weights, thresholds). Reused by:
- `scripts/run_riskometer.py` — run just the Risk-O-Meter + its own mini-PDF, standalone.
- `scripts/generate_risk_calculation_doc.py` — writes a transparent, stock-by-stock `.docx`
  showing the actual numbers behind one portfolio's score.

The methodology is also written up in `Riskometer_Manual_Calculation_Guide_v1.docx` and
`Riskometer_Scoring_Methodology_v1.docx` (generated by `scripts/generate_riskometer_*.py`).

---

## Stock Style classification (`stock_style.py`)

Scores every holding — and, for context, roughly 7,000 companies in the broader universe — on
four styles:

- **Growth** — is the business expanding fast? (EPS/revenue/profit CAGR, ROE/ROCE)
- **Value** — is the stock cheap for what you get? (low P/E, P/B, EV/EBITDA; high dividend yield)
- **Momentum** — has the price been winning lately? (6–12 month returns vs. index)
- **Quality** — is this a well-run, financially strong business? (high ROE/ROCE, low Debt/Equity, high interest cover)

(Full definitions in `definitions.txt`.) Each stock gets a percentile-based 0–100 score per
style relative to the whole universe, and is tagged with a Primary and Secondary style plus a
letter rating band (Exceptional → Very Weak), configured in `style_config.json`.

Inputs are entirely Excel-based: `Data_Growth.xlsx`, `Data_Value.xlsx`, `Data_Quality.xlsx`,
`Data_Liquidity.xlsx`, plus the `Data_NSE`/`Data_BSE` monthly price folders and
`Data_Nifty_50.csv` (for the Momentum calculation). Parsed price history is cached as parquet
under `.style_cache/` for speed.

Methodology write-ups: `Stock_Style_Classification_Methodology_v1.docx` and
`Stock_Style_Rating_and_Scoring_Methodology_v1.docx`.

---

## The database (`market_etl/`)

Tables in the `market_data` Postgres database (see `market_etl/models.py`):

| Table | Purpose |
|---|---|
| `sector_industry_mapping` | Valid (sector, industry) pairs — a lookup table |
| `company_master` | One row per ISIN: name, sector, industry |
| `daily_market_data` | (isin, trade_date): close price, market cap, volume, turnover |
| `fundamentals` | (isin, financial_year): ROE, ROCE, interest cover, debt/equity |
| `benchmark_data` | (index_name, trade_date): NIFTY 50 close, via yfinance |

`readers.py` parses the vendor's ("ACE Equity") Excel format — auto-detecting the header row
and renaming ACE's cryptic column names into clean snake_case. `services.py` orchestrates the
loads (historical bulk import, daily update, benchmark refresh). `repository.py` does chunked
upserts (`INSERT ... ON CONFLICT`) so re-running an import is always safe.

Setup and commands are documented in **`DATABASE_ETL.md`** — that's the file to read if you
need to (re)build the database from scratch or run a daily/historical import.

Useful commands:
```bash
python -m scripts.create_database                                  # create tables
python -m scripts.import_history --data-dir Data --master-file Daily_Data.xlsx   # one-time historical load
python -m scripts.daily_update --file Daily_Data.xlsx               # after refreshing the ACE workbook
```

---

## Data files — what's what

- **`Daily_Data.xlsx`** (root) — the current "master" ACE export: prices + sector/industry +
  fundamentals for the latest date. Used by the database daily update and by tests.
- **`Data/`** (root) — historical monthly ACE workbooks (prices only, no sector/fundamentals),
  used for the one-time historical database import.
- **`Data_Growth.xlsx` / `Data_Value.xlsx` / `Data_Quality.xlsx` / `Data_Liquidity.xlsx`** —
  Accord factor-data spreadsheets, used only by Stock Style classification.
- **`Data_BSE/` / `Data_NSE/`** — monthly price history by exchange, used by Stock Style for
  momentum/volatility calculations.
- **`Data_Nifty_50.csv` / `Data_Nifty_150.csv` / `Data_Nifty_500.csv`** (root) — daily index
  closes used by `portfolio_returns.py` for the returns-vs-benchmark report section.

> ⚠️ **`"Portfolio Analyzer Data/"` is a full, byte-for-byte duplicate** of `Data`, `Data_BSE`,
> `Data_NSE`, and all four `Data_*.xlsx` factor files (~17MB+ stored twice). Stock Style
> classification reads from this copy; the database ETL and `portfolio_returns.py` read the
> root copies directly. Nothing is broken by this, but it's worth knowing so you don't update
> one copy and wonder why nothing changed — you likely need to update both, or better,
> deduplicate them.

---

## Configuration & secrets

- **`config.py`** (root) — plain constants: file paths, the `BENCHMARKS`/`SECTORAL_INDICES`
  URL dictionaries, and a **hard-coded Gemini API key**.
- **`market_etl/config.py`** — a proper `.env`-driven settings object (`DATABASE_URL`,
  `DAILY_ACE_FILE`, `HISTORICAL_DATA_DIR`, `LOG_LEVEL`, `BENCHMARK_SYMBOL/NAME`).
- **`gemini_mapper.py`** — the only use of the Gemini API in this project: fuzzy-matching a
  broker's arbitrary column headers onto the four standard holdings fields. Not used for any
  other "AI" feature.

> ⚠️ **Security note:** the same Gemini API key is hard-coded in `config.py`,
> `main_industry.py`, `.env`, and a standalone `apikey.txt`. Since this folder isn't in git,
> it's not "leaked" in the source-control sense, but it's worth rotating and consolidating to
> the `.env`-only pattern that `market_etl/config.py` already uses — especially before this
> project ever goes into a git repo or gets shared.

---

## Tests

Only `tests/` is wired into pytest (`pyproject.toml` → `testpaths = ["tests"]`):

- **`tests/test_readers.py`** — checks the ACE Excel readers correctly find the header row and
  parse real workbooks (`Daily_Data.xlsx`, a historical `Data/*.xlsx` file).
- **`tests/test_riskometer.py`** — checks the Risk-O-Meter's quality-scoring edge cases: ETFs
  excluded, Interest Cover waived for banks/NBFCs, incomplete-fundamentals handling.

The various `test_*.py` files sitting at the **project root** (`test.py`, `test_analysis.py`,
`test_charts.py`, `test_market_cap.py`, `test_parser.py`, `test_sector.py`) are leftover manual
smoke scripts from building `main.py` — they're not real assertions-based tests and pytest
never runs them (only `tests/` is scoped).

Run the real test suite with:
```bash
pytest
```

---

## Known rough edges (nothing broken, just worth knowing)

- **Duplicate data folder** — `"Portfolio Analyzer Data/"` mirrors the root data files (see above).
- **Stock Style isn't wired to Postgres** yet, unlike the Risk-O-Meter — same data, two pipelines.
- **`create_table.py`** — an orphaned early Postgres experiment (different DB name, different
  driver, a table with no counterpart in `market_etl/models.py`). Safe to ignore or delete.
- **`main_industry.py`** — the pre-refactor monolith, kept alongside `main.py`.
- **API key hard-coded in 4 places** — see [Configuration & secrets](#configuration--secrets).
- **`sectoral_fundamentals.py`** looks unfinished — one methodology doc claims Value metrics are
  benchmarked against a stock's NSE sectoral index, but the actual scoring code
  (`stock_style_scoring.py`) doesn't yet consume `sectoral_fundamentals.csv`.
- **`October.xlsx`** and the empty **`.agents/`** folder aren't referenced anywhere — orphaned.
- **`sector_mapping.py`** has an old, commented-out version of its own functions sitting at the top of the file.

---

## Quick reference

| I want to... | Run |
|---|---|
| Generate a full client portfolio report | `python main.py` |
| Rebuild the database schema | `python -m scripts.create_database` |

## Web accounts and roles

The web application has database-backed accounts with two roles:

- **Client** — can register, sign in, upload and analyze portfolios, see only their own history,
  download reports, and compare any two of their completed analyses.
- **Admin** — can see every client and analysis, create client accounts, manage the data center,
  and temporarily enter a client's workspace using **Work as client**. The impersonation banner
  remains visible until the admin returns to their own workspace.

Create the first administrator interactively (there is no insecure default password):

```bash
python -m scripts.create_admin --email admin@example.com --name "Portfolio Admin"
```

Then run `npm run dev` and sign in at `http://localhost:3001/login`. For production, set a
random `AUTH_SECRET` of at least 32 characters; local development generates a private stable
secret under `runtime/` automatically.
| Bulk-load historical price data | `python -m scripts.import_history --data-dir Data --master-file Daily_Data.xlsx` |
| Refresh today's data | `python -m scripts.daily_update --file Daily_Data.xlsx` |
| Run just the Risk-O-Meter | `python -m scripts.run_riskometer --holdings <file>` |
| Run the real test suite | `pytest` |
