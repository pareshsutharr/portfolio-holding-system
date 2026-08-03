import pandas as pd
import os

from config import (
    BENCHMARKS,
    BENCHMARK_KEYS,
    BENCHMARK_REFRESH
)



# ==========================================
# LOAD CSV FILE
# ==========================================

def load_csv(file_path):

    if not os.path.exists(file_path):
        raise FileNotFoundError(
            f"File not found: {file_path}"
        )

    df = pd.read_csv(file_path)

    return df


# ==========================================
# STANDARDIZE SECTOR DATA
# ==========================================

def standardize_sector_data(
    sector_df
):

    required_columns = [
        "Sector",
        "Weight"
    ]


    for column in required_columns:

        if column not in sector_df.columns:

            raise Exception(
                f"{column} missing from benchmark sector data."
            )


    sector_df = sector_df[
        required_columns
    ].copy()


    sector_df.rename(
        columns={
            "Sector": "sector",
            "Weight": "benchmark_weight"
        },
        inplace=True
    )


    sector_df["sector"] = (
        sector_df["sector"]
        .astype(str)
        .str.strip()
    )


    sector_df["benchmark_weight"] = pd.to_numeric(
        sector_df["benchmark_weight"],
        errors="coerce"
    )


    sector_df.dropna(
        subset=[
            "sector",
            "benchmark_weight"
        ],
        inplace=True
    )


    sector_df.reset_index(
        drop=True,
        inplace=True
    )


    return sector_df


# ==========================================
# STANDARDIZE HOLDINGS DATA
# ==========================================

def standardize_holdings_data(
    holdings_df
):

    if holdings_df is None:

        return pd.DataFrame(
            columns=[
                "company",
                "benchmark_weight"
            ]
        )


    required_columns = [
        "Company",
        "Weight"
    ]


    for column in required_columns:

        if column not in holdings_df.columns:

            raise Exception(
                f"{column} missing from benchmark holdings data."
            )


    holdings_df = holdings_df[
        required_columns
    ].copy()


    holdings_df.rename(
        columns={
            "Company": "company",
            "Weight": "benchmark_weight"
        },
        inplace=True
    )


    holdings_df["company"] = (
        holdings_df["company"]
        .astype(str)
        .str.strip()
    )


    holdings_df["benchmark_weight"] = pd.to_numeric(
        holdings_df["benchmark_weight"],
        errors="coerce"
    )


    holdings_df.dropna(
        subset=[
            "company",
            "benchmark_weight"
        ],
        inplace=True
    )


    holdings_df.reset_index(
        drop=True,
        inplace=True
    )


    return holdings_df


# ==========================================
# LOAD BENCHMARK DATA
# ==========================================

def load_benchmark_data(
    benchmark_key,
    refresh=BENCHMARK_REFRESH
):

    benchmark = BENCHMARKS[
        benchmark_key
    ]

    sector_file = benchmark["sector_file"]

    holdings_file = benchmark["holdings_file"]

    pdf_file = benchmark["pdf_file"]

    if refresh:

        from benchmark_fetcher import download_factsheet

        from benchmark_parser import parse_benchmark

        download_factsheet(
            benchmark_key
        )

        parsed_data = parse_benchmark(
            benchmark_key
        )

        sector_df = parsed_data["sector"]

        holdings_df = parsed_data["holdings"]


    elif (
        os.path.exists(sector_file)
        and
        os.path.exists(holdings_file)
    ):

        sector_df = load_csv(
            sector_file
        )

        holdings_df = load_csv(
            holdings_file
        )


    elif os.path.exists(pdf_file):

        from benchmark_parser import parse_benchmark

        parsed_data = parse_benchmark(
            benchmark_key
        )

        sector_df = parsed_data["sector"]

        holdings_df = parsed_data["holdings"]


    else:

        from benchmark_fetcher import download_factsheet

        from benchmark_parser import parse_benchmark

        download_factsheet(
            benchmark_key
        )

        parsed_data = parse_benchmark(
            benchmark_key
        )

        sector_df = parsed_data["sector"]

        holdings_df = parsed_data["holdings"]


    sector_df = standardize_sector_data(
        sector_df
    )


    holdings_df = standardize_holdings_data(
        holdings_df
    )


    print("\n========== BENCHMARK DATA LOADED ==========\n")

    print(f"Benchmark       : {benchmark['name']}")
    print(f"Sector Records  : {len(sector_df)}")
    print(f"Holding Records : {len(holdings_df)}")


    return {

        "key": benchmark_key,

        "name": benchmark["name"],

        "sector": sector_df,

        "holdings": holdings_df

    }


# ==========================================
# LOAD ALL BENCHMARKS
# ==========================================

def load_all_benchmarks(
    refresh=BENCHMARK_REFRESH
):

    benchmark_data = []


    for benchmark_key in BENCHMARK_KEYS:

        data = load_benchmark_data(
            benchmark_key,
            refresh
        )

        benchmark_data.append(
            data
        )


    return benchmark_data



# ==========================================
# DISPLAY DATA
# ==========================================

def display_data(title, df):

    print("\n")
    print("=" * 60)
    print(title)
    print("=" * 60)

    print(df.to_string(index=False))

    print("\nTotal Records:", len(df))



# ==========================================
# MAIN
# ==========================================

def main():

    print("\nLoading benchmark data...")


    all_benchmarks = load_all_benchmarks()


    for benchmark_data in all_benchmarks:

        display_data(
            f"{benchmark_data['name'].upper()} SECTOR ALLOCATION",
            benchmark_data["sector"]
        )


        display_data(
            f"{benchmark_data['name'].upper()} TOP HOLDINGS",
            benchmark_data["holdings"]
        )



    print("\nBenchmark reader completed successfully ✅")



if __name__ == "__main__":
    main()
