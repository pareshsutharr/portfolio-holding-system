"""Calculate the Portfolio Risk-O-Meter and generate its PDF report."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from market_etl.config import Settings
from market_etl.database import build_engine
from riskometer import Riskometer
from riskometer_report import generate_riskometer_pdf


def read_holdings(path: Path) -> pd.DataFrame:
    raw = pd.read_excel(path, header=None)
    header_row = None
    for index, row in raw.head(30).iterrows():
        labels = {str(value).strip().lower() for value in row.dropna()}
        if "isin" in labels and ("closing value" in labels or "value" in labels):
            header_row = int(index)
            break
    if header_row is None:
        raise ValueError("Could not find ISIN and Closing Value columns in holdings file.")
    frame = pd.read_excel(path, header=header_row)
    normalized = {str(column).strip().lower(): column for column in frame.columns}
    name_column = normalized.get("stock name") or normalized.get("security name") or normalized.get("company name")
    value_column = normalized.get("closing value") or normalized.get("value")
    if not name_column or not value_column:
        raise ValueError("Holdings file must contain a security name and closing value.")
    return frame[[name_column, normalized["isin"], value_column]].rename(
        columns={name_column: "security_name", normalized["isin"]: "isin", value_column: "value"}
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--holdings", type=Path, default=Path("test_files/holdings.xlsx"))
    parser.add_argument("--config", type=Path, default=Path("riskometer_config.json"))
    parser.add_argument("--output", type=Path, default=Path("output/riskometer_report.pdf"))
    args = parser.parse_args()
    settings = Settings.from_env()
    analysis = Riskometer(build_engine(settings.database_url), args.config).analyze(
        read_holdings(args.holdings)
    )
    generate_riskometer_pdf(analysis, args.output)
    print(f"Overall Portfolio Risk: {analysis['overall_score']:.2f} - {analysis['overall_level']}")
    for result in analysis["results"]:
        print(f"{result.name.replace('_', ' ').title()} Risk: {result.score:.2f} - {result.level}")
    print(f"PDF: {args.output}")


if __name__ == "__main__":
    main()
