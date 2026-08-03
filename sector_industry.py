import pandas as pd

from config import ISIN_MASTER_FILE

# =====================================
# READ ISIN MASTER
# =====================================

def load_isin_master():

    isin_master = pd.read_excel(
        ISIN_MASTER_FILE,
        header=3
    )

    print("\n========== ISIN MASTER ==========\n")

    print(isin_master.columns.tolist())

    # ---------------------------------
    # Keep Required Columns
    # ---------------------------------

    isin_master = isin_master[
        [
            "CD_ISIN No",
            "CD_Sector",
            "CD_Industry1"
        ]
    ].copy()

    # ---------------------------------
    # Rename Columns
    # ---------------------------------

    isin_master.rename(
        columns={
            "CD_ISIN No": "isin",
            "CD_Sector": "sector",
            "CD_Industry1": "industry"
        },
        inplace=True
    )

    # ---------------------------------
    # Clean ISIN
    # ---------------------------------

    isin_master["isin"] = (
        isin_master["isin"]
        .astype(str)
        .str.strip()
    )

    return isin_master


# =====================================
# MERGE SECTOR & INDUSTRY
# =====================================

def add_sector_industry(portfolio_df):

    isin_master = load_isin_master()

    enriched_df = pd.merge(
        portfolio_df,
        isin_master,
        on="isin",
        how="left"
    )

    # ---------------------------------
    # Replace Missing Values
    # ---------------------------------

    enriched_df["sector"] = (
        enriched_df["sector"]
        .fillna("Unknown")
    )

    enriched_df["industry"] = (
        enriched_df["industry"]
        .fillna("Unknown")
    )

    # ---------------------------------
    # Match Statistics
    # ---------------------------------

    matched = (
        enriched_df["sector"] != "Unknown"
    ).sum()

    unmatched = len(enriched_df) - matched

    print("\n========== SECTOR / INDUSTRY MATCH ==========\n")

    print(f"Total Holdings : {len(enriched_df)}")
    print(f"Matched        : {matched}")
    print(f"Unmatched      : {unmatched}")

    if unmatched > 0:

        print("\n========== UNMATCHED STOCKS ==========\n")

        print(

            enriched_df[
                enriched_df["sector"] == "Unknown"
            ][
                [
                    "security_name",
                    "isin"
                ]
            ].to_string(index=False)

        )

    print("\n========== ENRICHED PORTFOLIO ==========\n")

    print(enriched_df.to_string(index=False))

    return enriched_df