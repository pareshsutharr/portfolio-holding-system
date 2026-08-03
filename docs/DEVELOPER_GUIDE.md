# Portfolio Analyzer — Developer and Operations Guide

## Components

- `web/` — Next.js App Router, React, TypeScript, Tailwind CSS, Recharts.
- `api/` — FastAPI HTTP adapter.
- `portfolio_service.py` — reusable orchestration around existing calculations.
- `yahoo_prices.py` — NSE-first/BSE-fallback current quote refresh and valuation.
- `market_etl/` — SQLAlchemy/PostgreSQL models and loaders.
- `runtime/analyses/` — private per-run uploads, JSON results, and PDFs.
- `output/` — legacy CLI output and shared chart working files.

## Prerequisites

- Python 3.12
- Node.js 20 or newer
- PostgreSQL 16

## Installation

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install -r requirements-dev.txt
npm --prefix web install
brew services start postgresql@16
.venv/bin/python -m scripts.create_database
```

Copy `.env.example` to `.env` and set `DATABASE_URL`. Keep API keys and
passwords out of source control.

## Development

Run both services:

```bash
./run_web.sh
```

Or independently:

```bash
.venv/bin/python -m uvicorn api.main:app --reload --port 8000
npm --prefix web run dev
```

The web interface is at `http://localhost:3001` and the OpenAPI explorer is at
`http://localhost:8000/docs`.

## Verification

```bash
.venv/bin/python -m compileall -q api portfolio_service.py market_etl
npm test
npm --prefix web run lint
npm --prefix web run build
curl http://127.0.0.1:8000/health
```

## API contract

- `GET /health` — service and database connectivity.
- `GET /api/dashboard` — recent analysis summaries.
- `POST /api/analyses/preview` — multipart Excel upload and local mapping.
- `POST /api/analyses` — execute a previewed upload.
- `GET /api/analyses/{id}` — status and normalized result.
- `GET /api/analyses/{id}/report` — generated PDF.

## Production notes

Run Next.js using its standalone build and Uvicorn behind a reverse proxy.
Configure one public origin, TLS, upload limits, authentication, and a durable
private artifact volume. The current synchronous analysis endpoint is suitable
for a single-analyst local deployment; multi-user deployment should move work
to a PostgreSQL-backed job queue and isolate shared chart generation.
