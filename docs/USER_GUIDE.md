# Portfolio Analyzer — User Guide

## Start the application

From the project directory:

```bash
./run_web.sh
```

Open `http://localhost:3001`.

To stop a previously running copy:

```bash
npm run stop
```

To stop and immediately restart both services:

```bash
npm run restart
```

## Analyze a portfolio

1. Select **New analysis**.
2. Upload an Excel (`.xlsx` or `.xls`) holdings statement up to 20 MB.
3. Review the detected holdings count, value, and mapped columns.
4. Select **Run analysis**. A full run calculates allocation, risk, stock
   style, returns, benchmark comparisons, charts, and the PDF.
5. Open the interactive analysis or download the PDF report.

## Current market prices

During the full analysis, CMP is refreshed from Yahoo Finance. The system uses
the NSE ticker first and the BSE ticker as fallback. ETF tickers supported by
the portfolio are resolved from their ISIN.

`Value` is recalculated as `Quantity × Yahoo CMP`, so allocation percentages,
risk calculations, charts, UI tables, and the generated PDF all use the same
current valuation. If Yahoo Finance temporarily has no quote for a security,
the uploaded workbook CMP is retained and marked as `Uploaded workbook`.

## Required holdings fields

The workbook must contain columns representing:

- Security/company name
- ISIN
- Quantity
- Closing/current market value

Common broker labels such as `Stock Name`, `ISIN`, `Qty`, and `Closing Value`
are detected locally. Unfamiliar labels can use the configured Gemini mapper.

## Reading the results

- **Allocation** shows portfolio weight by sector, industry, and market cap.
- **Concentration** highlights dependence on the largest holdings.
- **Risk-O-Meter** combines seven configured factors on a 0–100 scale.
- **Coverage** tells you how much portfolio data supported each score.
- **Stock style** classifies holdings across Growth, Value, Momentum, and
  Quality.
- **Performance** compares simulated current holdings with Nifty benchmarks.

Scores are analytical aids, not investment recommendations.

## Common issues

- If the database status fails, confirm PostgreSQL is running:
  `brew services start postgresql@16`.
- If port 3000 is occupied, stop the other local development server.
- If a workbook cannot be read, export it as a standard `.xlsx` file without
  password protection.
- Vendor workbooks without a default Excel style are supported safely.
