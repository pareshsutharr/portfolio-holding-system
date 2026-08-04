# Portfolio Analyzer

The product is a single repository with a Next.js 16 App Router frontend and a
Python analysis service. Next.js owns the browser application, navigation,
authentication client, dashboards, uploads, reports, and production build. The
Python service remains the calculation boundary for the existing Excel,
portfolio-risk, market-data, chart, and PDF pipelines.

## Local development

Install both runtimes, then start the API and web application in separate
terminals:

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
npm install
npm run dev:api
```

```bash
npm run dev
```

The frontend uses `http://127.0.0.1:8000` automatically in development. Set
`NEXT_PUBLIC_API_URL` when the API is hosted on another origin.

## Verification

```bash
npm run lint
npm run build
npm run test:api
```

## Deployment

Configure these secrets in the deployment environment:

- `DATABASE_URL` — Supabase PostgreSQL connection string
- `AUTH_SECRET` — stable, randomly generated signing secret
- `GEMINI_API_KEY` — only when AI-assisted column mapping is enabled
- `ALLOWED_ORIGINS` — required when the frontend and API use different origins
- `NEXT_PUBLIC_API_URL` — omit for a same-origin API; otherwise use the public
  API origin without a trailing slash

The former frontend checkout under `web/` is no longer part of the build. The
canonical application source is now `src/` at the repository root.
