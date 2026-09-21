# Portfolio Analyzer

The product is a single repository with a Next.js 16 App Router frontend and a
Python analysis service. Next.js owns the browser application, navigation,
authentication client, dashboards, uploads, reports, and production build. The
Python service remains the calculation boundary for the existing Excel,
portfolio-risk, market-data, chart, and PDF pipelines.

## Local development

Install PostgreSQL 16 (or newer) and both runtimes. Create the local database,
then start the API and web application in separate terminals:

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
npm install
createdb market_data  # run once
.venv/bin/python -m scripts.create_database
```

Start both the API and web application with one command:

```bash
npm run dev
```

Or launch both local processes together with `./run_web.sh`; the application
opens at `http://localhost:3001`.

The frontend uses `http://127.0.0.1:8000` automatically in development. Set
`NEXT_PUBLIC_API_URL` when the API is hosted on another origin.

## Verification

```bash
npm run lint
npm run build
npm run test:api
```

## Local configuration

Copy `.env.example` to `.env` and configure:

- `DATABASE_URL` — local PostgreSQL connection string (normally `localhost:5432`)
- `AUTH_SECRET` — stable, randomly generated signing secret
- `GEMINI_API_KEY` — only when AI-assisted column mapping is enabled
- `ALLOWED_ORIGINS` — local frontend origins
- `NEXT_PUBLIC_API_URL` — local FastAPI address

Reference workbooks and uploaded analysis files stay on this computer under the
project and `runtime/` directories. No hosted database or cloud file storage is
used.

## Daily NIFTY sector allocations

`npm run dev` and `npm start` also run the local ingestion scheduler. At 07:00
Asia/Kolkata it downloads the official NIFTY 50, NIFTY Midcap 150, and NIFTY
500 factsheets, validates only their Sector Representation tables, stores dated
PostgreSQL snapshots, and atomically updates `data/*-sectors.txt`. Downloaded
PDFs are temporary and are removed after every run.

Run an immediate independent refresh with:

```bash
.venv/bin/python -m scripts.update_sector_allocations
```

Administrators can monitor history, compare factsheet dates, and trigger a
background refresh at `/admin/sector-allocations`. Requests are retried and
rate-limited; Playwright is used only as a fallback. If fallback browsing is
needed on a new machine, install its local browser once with
`.venv/bin/playwright install chromium`.

The former frontend checkout under `web/` is no longer part of the build. The
canonical application source is now `src/` at the repository root.
# portfolio-analyzer
