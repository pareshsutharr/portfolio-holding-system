# Portfolio Risk Analyzer database and ETL

This package creates and maintains the PostgreSQL `market_data` database. It is
separate from the existing report-generation modules, so later risk calculations
can consume the database without coupling themselves to Excel.

## Schema assumptions

- ISIN values are stored uppercase and are the company key.
- ACE market cap and turnover are stored exactly in the units exported by ACE;
  the ETL does not silently rescale them. `NDP_Volume ('000)` likewise remains in
  thousands.
- Sector and industry are nullable because the historical monthly files do not
  contain them. A composite foreign key protects populated sector/industry pairs.
- Numeric columns use `NUMERIC`, not floating point, to avoid financial rounding
  surprises.
- `updated_at` audit columns were added to mutable master/fundamental tables.
- Re-importing market history skips an existing `(isin, trade_date)` record.
  Daily master and fundamental rows are updated with the latest ACE values.
- The supplied monthly files contain no sector, industry, or fundamental fields.
  Use `--master-file Daily_Data.xlsx` during the historical import to enrich those
  tables. Without it, history and basic company names still load successfully.

## Setup

Create the empty PostgreSQL database once:

```sql
CREATE DATABASE market_data;
```

Create a Python 3.12+ virtual environment, then:

```powershell
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and set `DATABASE_URL`. Do not commit the real password.

## Create tables

```powershell
python -m scripts.create_database
```

## One-time historical import

The directory is searched recursively, so both `Data/January_2026.xlsx` and the
documented `Data/January_2026/*.xlsx` layout work.

```powershell
python -m scripts.import_history --data-dir Data --master-file Daily_Data.xlsx
```

All files run in one transaction. If a workbook is invalid, PostgreSQL rolls the
import back so it can be corrected and safely rerun.

## Daily update

After refreshing the ACE workbook:

```powershell
python -m scripts.daily_update --file Daily_Data.xlsx
```

This upserts company details and yearly fundamentals, inserts unseen daily market
records, and downloads missing `^NSEI` closes from Yahoo Finance under `NIFTY 50`.

## Verification

Reader tests use the real example workbooks but do not require PostgreSQL:

```powershell
pytest tests/test_readers.py
```
