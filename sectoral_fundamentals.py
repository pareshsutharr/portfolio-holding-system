"""Downloads NSE sectoral index factsheets and extracts the Fundamentals
table (P/E, P/B, Dividend Yield) that Stock Style Value scoring will
benchmark against, instead of the whole-market median.

The Fundamentals section in these factsheets has no grid/border lines, so
pdfplumber's extract_tables() cannot reliably capture it (confirmed on the
Nifty Bank factsheet -- the header row extracts cleanly but the value row
comes back empty). It is extracted from the raw page text instead.
"""

import os
import re
import time

import pandas as pd
import pdfplumber
import requests

from config import SECTORAL_FUNDAMENTALS_FILE, SECTORAL_INDICES


HEADER_PATTERN = re.compile(r"P/E\s+P/B\s+Dividend Yield")
VALUES_LINE_PATTERN = re.compile(r"^\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*$")

MAX_DOWNLOAD_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 3


# ==========================================
# DOWNLOAD FACTSHEET
# ==========================================

def download_sectoral_factsheet(index_key):

    index = SECTORAL_INDICES[index_key]

    file_path = index["pdf_file"]

    os.makedirs(
        os.path.dirname(file_path),
        exist_ok=True
    )

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    last_error = None

    for attempt in range(1, MAX_DOWNLOAD_ATTEMPTS + 1):

        try:
            print(f"Downloading {index['name']} factsheet (attempt {attempt})...")

            response = requests.get(
                index["url"],
                headers=headers,
                timeout=30
            )

            response.raise_for_status()

            if not response.content.startswith(b"%PDF"):
                raise ValueError(
                    f"URL did not return a PDF (got {response.content[:30]!r})"
                )

            with open(file_path, "wb") as file:
                file.write(response.content)

            return file_path

        except Exception as error:
            last_error = error

            if attempt < MAX_DOWNLOAD_ATTEMPTS:
                time.sleep(RETRY_DELAY_SECONDS)

    raise RuntimeError(
        f"Failed to download {index['name']} after {MAX_DOWNLOAD_ATTEMPTS} attempts: {last_error}"
    )


# ==========================================
# EXTRACT FUNDAMENTALS FROM PDF TEXT
# ==========================================

def extract_fundamentals(pdf_path):

    with pdfplumber.open(pdf_path) as pdf:
        full_text = "\n".join(page.extract_text() or "" for page in pdf.pages)

    header_match = HEADER_PATTERN.search(full_text)

    if not header_match:
        raise ValueError(
            f"Fundamentals header (P/E, P/B, Dividend Yield) not found in {pdf_path}"
        )

    # The values row is not always the line immediately after the header --
    # some factsheets (e.g. Nifty Energy) interleave unrelated chart-legend
    # text in between. Scan forward for the first line that is purely three
    # numbers.
    remaining_lines = full_text[header_match.end():].splitlines()

    for line in remaining_lines[:10]:
        values_match = VALUES_LINE_PATTERN.match(line)
        if values_match:
            pe, pb, div_yield = values_match.groups()
            return {
                "pe": float(pe),
                "pb": float(pb),
                "dividend_yield": float(div_yield)
            }

    raise ValueError(
        f"Fundamentals values row (three numbers) not found near header in {pdf_path}"
    )


# ==========================================
# FETCH ONE SECTORAL INDEX
# ==========================================

def _is_valid_pdf(file_path):

    if not os.path.exists(file_path):
        return False

    with open(file_path, "rb") as file:
        return file.read(4) == b"%PDF"


def fetch_sectoral_fundamentals(index_key, refresh=False):

    index = SECTORAL_INDICES[index_key]

    pdf_file = index["pdf_file"]

    if refresh or not _is_valid_pdf(pdf_file):
        download_sectoral_factsheet(index_key)

    fundamentals = extract_fundamentals(pdf_file)

    return {
        "index_key": index_key,
        "index_name": index["name"],
        "nse_sector": index["nse_sector"],
        **fundamentals
    }


# ==========================================
# FETCH ALL SECTORAL INDICES
# ==========================================

def fetch_all_sectoral_fundamentals(refresh=False):

    rows = []

    for index_key in SECTORAL_INDICES:

        try:
            rows.append(fetch_sectoral_fundamentals(index_key, refresh))

        except Exception as error:
            print(f"Skipped {index_key}: {error}")

    df = pd.DataFrame(rows)

    os.makedirs(
        os.path.dirname(SECTORAL_FUNDAMENTALS_FILE),
        exist_ok=True
    )

    df.to_csv(SECTORAL_FUNDAMENTALS_FILE, index=False)

    print(f"\nSaved {len(df)} sectoral fundamentals to {SECTORAL_FUNDAMENTALS_FILE}")

    return df


# ==========================================
# LOAD SAVED SECTORAL FUNDAMENTALS
# ==========================================

def load_sectoral_fundamentals():

    return pd.read_csv(SECTORAL_FUNDAMENTALS_FILE)


if __name__ == "__main__":
    print(fetch_all_sectoral_fundamentals())
