# Portfolio Analyzer Web Product — Implementation Plan

## 1. Product goal

Convert the existing command-line portfolio analyzer into a responsive web
product where an analyst can upload a holdings workbook, verify detected
columns, run the complete analysis, explore the results interactively, and
download a professionally generated PDF report.

The existing Python calculation and ReportLab code remains the source of truth.
Next.js supplies the product interface. A FastAPI service adapts the Python
pipeline into stable, testable HTTP endpoints.

## 2. Target users and primary workflow

Primary user: a portfolio analyst preparing a client portfolio review.

1. Open the dashboard and see data freshness and recent analyses.
2. Start a new analysis and upload an `.xlsx` holdings statement.
3. Review the detected header and mapped fields.
4. Correct mappings if required and validate holdings.
5. Run analysis while viewing stage-by-stage progress.
6. Review overview, allocation, risk, style, performance, and benchmark tabs.
7. Download the PDF report and retain the analysis in report history.

## 3. Information architecture

- **Dashboard** — system status, portfolio KPIs, recent reports, quick action.
- **New analysis** — upload, column mapping, validation, processing, completion.
- **Analysis detail**
  - Overview
  - Holdings
  - Allocation
  - Risk-O-Meter
  - Stock style
  - Performance
  - Benchmark comparison
- **Reports** — completed/failed analyses and artifact downloads.
- **Data health** — database counts, source freshness, benchmark status.
- **Settings** — paths and non-secret runtime status; secrets remain server-only.

## 4. Technical architecture

```text
Browser
  |
  v
Next.js App Router (TypeScript)
  - responsive UI and charts
  - upload/mapping workflow
  - typed API client
  - route handlers proxy /api/* to Python
  |
  v
FastAPI service (Python 3.12)
  - upload validation
  - pipeline orchestration
  - job status and error model
  - JSON serialization
  - PDF artifact delivery
  |
  +--> existing analysis modules
  +--> existing ReportLab document generator
  +--> PostgreSQL market_data
  +--> controlled local market-data files
```

Next.js does not recalculate financial metrics. This prevents calculation drift
between the UI and PDF. The API returns normalized JSON used by both.

## 5. Backend refactor

- Extract `main.py` into an importable `PortfolioAnalysisService`.
- Replace fixed global input/output paths with a per-run context.
- Keep `main.py` as a backwards-compatible CLI wrapper.
- Add Pydantic request/response schemas and safe numeric/date serialization.
- Add API routes:
  - `GET /health`
  - `GET /api/dashboard`
  - `POST /api/analyses/preview`
  - `POST /api/analyses`
  - `GET /api/analyses/{id}`
  - `GET /api/analyses/{id}/report`
  - `GET /api/data-health`
- Store run metadata and normalized results in PostgreSQL.
- Store uploaded workbooks and generated artifacts under a private run
  directory using generated IDs, never user-supplied paths.
- Ensure failures return a stage, user-safe explanation, and diagnostic ID.

## 6. UI/UX direction

Visual character: professional financial research desk—calm, dense enough for
analysts, but not spreadsheet-like. Use a warm off-white canvas, deep navy
navigation, restrained teal/amber risk accents, strong tabular typography, and
generous card spacing.

Core components:

- App shell with collapsible navigation and mobile drawer.
- KPI cards with contextual deltas/coverage, not decorative statistics.
- Accessible upload drop zone and file picker.
- Editable column-mapping controls with sample values.
- Processing timeline with seven meaningful analysis stages.
- Reusable chart card, legend, empty state, skeleton, and error state.
- Sortable/filterable holdings table.
- Risk gauge plus transparent factor score cards.
- Style matrix and holding-level style table.
- Benchmark allocation and return comparison charts.
- Report rows with status, date, portfolio value, risk, and download action.

## 7. Data and document strategy

- PostgreSQL remains authoritative for market/fundamental history.
- Existing Excel/CSV inputs remain supported in phase one behind repository
  adapters; duplicate data folders are not copied into the web application.
- Existing ReportLab output is preserved and changed to accept a run-specific
  destination.
- Generated PDF is exposed through an authenticated-safe download endpoint.
- A developer/operator guide documents installation, services, environment
  variables, database bootstrap, local development, production build, and
  troubleshooting.
- An end-user guide documents upload requirements and interpretation of every
  report section.

## 8. Security and reliability

- Secrets only in environment variables and never returned to the browser.
- File extension, MIME type, workbook size, and required-column validation.
- Generated filenames and directory containment checks.
- No execution of workbook macros.
- Database connection health checks and transactional run persistence.
- API CORS limited to configured UI origins.
- Structured logs with no holdings contents or credentials.
- Clear treatment of unavailable risk coverage instead of silent failures.

## 9. Test and acceptance plan

- Unit tests for header mapping, parsing, JSON serialization, and run paths.
- API tests for health, preview, analysis, validation errors, and download.
- Frontend lint/type/build checks.
- Browser tests at desktop and mobile widths:
  - dashboard renders
  - workbook upload and mapping
  - analysis completion
  - all analysis tabs
  - PDF download
  - error and empty states
- Existing `python main.py` workflow continues to work.

Acceptance criteria:

- A user can complete a portfolio analysis without using a terminal.
- UI metrics match the generated PDF for the same run.
- Refreshing an analysis URL retains the result.
- A failed run is visible and actionable.
- The app builds cleanly and the documented one-command local startup works.

## 10. Delivery sequence

1. Backend service extraction and API contract.
2. Next.js foundation and design system.
3. Dashboard and upload/mapping flow.
4. Analysis detail views and interactive charts.
5. Run persistence and artifact downloads.
6. Data-health/settings pages.
7. Tests, browser QA, documentation, and production handoff.

