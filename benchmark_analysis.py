import pandas as pd


# =====================================
# BENCHMARK ANALYSIS
# =====================================

def analyze_benchmark(
    analysis,
    benchmark_data
):

    # =====================================
    # LOAD BENCHMARK DATA
    # =====================================

    benchmark_name = benchmark_data["name"]

    benchmark_key = benchmark_data["key"]

    benchmark = benchmark_data["sector"].copy()

    benchmark_holdings = benchmark_data["holdings"].copy()

    # =====================================
    # CLEAN SECTOR NAMES
    # =====================================

    benchmark["sector"] = (

        benchmark["sector"]

        .astype(str)

        .str.strip()

    )

    # =====================================
    # CLIENT SECTOR DATA
    # =====================================

    client_sector = analysis["sector"][
        [
            "sector",
            "allocation_percent"
        ]
    ].copy()

    client_sector = client_sector.rename(

        columns={

            "allocation_percent": "client_weight"

        }

    )

    client_sector["sector"] = (

        client_sector["sector"]

        .astype(str)

        .str.strip()

    )

    # =====================================
    # MERGE
    # =====================================

    comparison = pd.merge(

        benchmark,

        client_sector,

        on="sector",

        how="outer"

    )

    # =====================================
    # FILL MISSING VALUES
    # =====================================

    comparison["benchmark_weight"] = (

        comparison["benchmark_weight"]

        .fillna(0)

    )

    comparison["client_weight"] = (

        comparison["client_weight"]

        .fillna(0)

    )

    # =====================================
    # DIFFERENCE
    # =====================================

    comparison["difference"] = (

        comparison["client_weight"]

        -

        comparison["benchmark_weight"]

    ).round(2)

    # =====================================
    # SORT
    # =====================================

    comparison = comparison.sort_values(

        by="benchmark_weight",

        ascending=False

    ).reset_index(drop=True)

    # =====================================
    # STORE INSIDE ANALYSIS
    # =====================================

    if "benchmarks" not in analysis:

        analysis["benchmarks"] = {}


    analysis["benchmarks"][benchmark_key] = {

        "key": benchmark_key,

        "name": benchmark_name,

        "sector": benchmark,

        "holdings": benchmark_holdings,

        "comparison": comparison

    }

    # =====================================
    # DEBUG
    # =====================================

    print(
        f"\n========== {benchmark_name.upper()} COMPARISON ==========\n"
    )

    print(comparison)

    return analysis


# =====================================
# ANALYZE ALL BENCHMARKS
# =====================================

def analyze_all_benchmarks(
    analysis,
    all_benchmark_data
):

    analysis["benchmarks"] = {}


    for benchmark_data in all_benchmark_data:

        analysis = analyze_benchmark(
            analysis,
            benchmark_data
        )


    return analysis
