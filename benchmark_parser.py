import pdfplumber
import pandas as pd
import os
import re

from config import (
    BENCHMARKS,
    BENCHMARK_KEYS
)


# ==========================================
# PATH CONFIGURATION
# ==========================================

OUTPUT_DIR = "benchmark/output"


# ==========================================
# CREATE OUTPUT DIRECTORY
# ==========================================

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


# ==========================================
# EXTRACT TABLES FROM PDF
# ==========================================

def extract_pdf_tables(pdf_path):

    all_tables = []

    print("\nReading PDF...")

    with pdfplumber.open(pdf_path) as pdf:

        print("Total pages:", len(pdf.pages))

        for page_no, page in enumerate(pdf.pages, start=1):

            tables = page.extract_tables()

            if tables:

                print(
                    f"Page {page_no}: {len(tables)} tables found"
                )

                for table in tables:
                    all_tables.append(table)


    return all_tables



# ==========================================
# CLEAN TABLE
# ==========================================

def clean_table(table):

    df = pd.DataFrame(table)


    # remove empty rows

    df.dropna(
        how="all",
        inplace=True
    )


    # remove empty columns

    df.dropna(
        axis=1,
        how="all",
        inplace=True
    )


    return df



# ==========================================
# IDENTIFY SECTOR TABLE
# ==========================================

def find_sector_table(tables):

    for table in tables:

        df = clean_table(table)


        text = " ".join(
            df.astype(str)
            .values
            .flatten()
        )


        if (
            "Sector" in text
            and
            "Weight" in text
        ):

            return df


    return None



# ==========================================
# IDENTIFY HOLDINGS TABLE
# ==========================================

def find_holdings_table(tables):

    for table in tables:

        df = clean_table(table)


        text = " ".join(
            df.astype(str)
            .values
            .flatten()
        )


        if (
            "Company" in text
            and
            "Weight" in text
        ):

            return df


    return None



# ==========================================
# PROCESS SECTOR DATA
# ==========================================

def process_sector_table(df):

    print("\nProcessing sector table...")


    df.columns = df.iloc[0]

    df = df.iloc[1:]


    df.columns = [
        str(c).strip()
        for c in df.columns
    ]


    df = df.iloc[:, :2]


    df.columns = [
        "Sector",
        "Weight"
    ]


    df["Weight"] = (
        df["Weight"]
        .astype(str)
        .str.replace("%","")
        .str.strip()
    )


    df["Weight"] = pd.to_numeric(
        df["Weight"],
        errors="coerce"
    )


    df.dropna(
        inplace=True
    )


    return df



# ==========================================
# PROCESS HOLDINGS DATA
# ==========================================

def process_holdings_table(df):

    print("\nProcessing holdings table...")


    df.columns = df.iloc[0]

    df = df.iloc[1:]


    df.columns = [
        str(c).strip()
        for c in df.columns
    ]


    df = df.iloc[:, :2]


    df.columns = [
        "Company",
        "Weight"
    ]


    df["Weight"] = (
        df["Weight"]
        .astype(str)
        .str.replace("%","")
        .str.strip()
    )


    df["Weight"] = pd.to_numeric(
        df["Weight"],
        errors="coerce"
    )


    df.dropna(
        inplace=True
    )


    return df



# ==========================================
# MAIN
# ==========================================

def parse_benchmark(
    benchmark_key
):

    benchmark = BENCHMARKS[
        benchmark_key
    ]

    pdf_file = benchmark["pdf_file"]

    sector_output = benchmark["sector_file"]

    holdings_output = benchmark["holdings_file"]

    tables = extract_pdf_tables(
        pdf_file
    )


    print(
        "\nTotal tables extracted:",
        len(tables)
    )


    sector_table = find_sector_table(
        tables
    )


    holdings_table = find_holdings_table(
        tables
    )


    sector_df = None

    holdings_df = None


    if sector_table is not None:

        sector_df = process_sector_table(
            sector_table
        )


        sector_df.to_csv(
            sector_output,
            index=False
        )


        print(
            "\nSector file created:"
        )

        print(
            sector_output
        )


    else:

        print(
            "\nSector table not found"
        )



    if holdings_table is not None:

        holdings_df = process_holdings_table(
            holdings_table
        )


        holdings_df.to_csv(
            holdings_output,
            index=False
        )


        print(
            "\nHoldings file created:"
        )

        print(
            holdings_output
        )


    else:

        print(
            "\nHoldings table not found"
        )


    if sector_df is None:

        raise Exception(
            "Benchmark sector table not found."
        )


    return {

        "key": benchmark_key,

        "name": benchmark["name"],

        "sector": sector_df,

        "holdings": holdings_df

    }


# ==========================================
# MAIN
# ==========================================

def main():

    for benchmark_key in BENCHMARK_KEYS:

        parse_benchmark(
            benchmark_key
        )



if __name__ == "__main__":

    main()
