import pandas as pd

from config import MCAP_MASTER_FILE

# =====================================
# LOAD MARKET CAP MASTER
# =====================================

def load_market_cap_master():

    mcap_master = pd.read_excel(
        MCAP_MASTER_FILE,
        header=1
    )

    print("\n========== MARKET CAP MASTER ==========\n")

    print(mcap_master.columns.tolist())

    # =====================================
    # KEEP REQUIRED COLUMNS
    # =====================================

    mcap_master = mcap_master[
        [
            "ISIN",
            "NSE Symbol",
            "BSE Symbol",
            "Categorization as per SEBI Circular dated Oct 6, 2017"
        ]
    ].copy()

    # =====================================
    # RENAME COLUMNS
    # =====================================

    mcap_master.rename(
        columns={
            "ISIN": "isin",
            "NSE Symbol": "nse_symbol",
            "BSE Symbol": "bse_symbol",
            "Categorization as per SEBI Circular dated Oct 6, 2017": "cap_category"
        },
        inplace=True
    )

    # =====================================
    # CLEAN DATA
    # =====================================

    mcap_master["isin"] = (
        mcap_master["isin"]
        .astype(str)
        .str.strip()
    )

    mcap_master["cap_category"] = (
        mcap_master["cap_category"]
        .astype(str)
        .str.strip()
    )

    for column in ("nse_symbol", "bse_symbol"):
        mcap_master[column] = (
            mcap_master[column]
            .fillna("")
            .astype(str)
            .str.strip()
            .replace({"nan": "", "-": ""})
        )

    return mcap_master


# =====================================
# MERGE MARKET CAP
# =====================================

def add_market_cap(portfolio_df):

    mcap_master = load_market_cap_master()

    portfolio_df = pd.merge(
        portfolio_df,
        mcap_master,
        on="isin",
        how="left"
    )

    is_etf = (
        portfolio_df["sector"].astype(str).str.upper().eq("ETF")
        | portfolio_df["security_name"].astype(str).str.contains(
            r"\bETF\b|GOLD\s*BEES|NETF(?:GOLD|SILVER)",
            case=False,
            regex=True,
            na=False,
        )
    )
    portfolio_df.loc[is_etf, "cap_category"] = "ETF"
    portfolio_df["cap_category"] = portfolio_df["cap_category"].fillna("Unknown")

    matched = portfolio_df["cap_category"].isin(
        ["Large Cap", "Mid Cap", "Small Cap"]
    ).sum()
    etfs = is_etf.sum()

    unmatched = (portfolio_df["cap_category"] == "Unknown").sum()

    print("\n========== MARKET CAP MATCH ==========\n")

    print(f"Total Holdings : {len(portfolio_df)}")
    print(f"Equity Matched : {matched}")
    print(f"ETFs (N/A)     : {etfs}")
    print(f"Unmatched      : {unmatched}")

    if unmatched > 0:

        print("\n========== UNMATCHED MARKET CAP ==========\n")

        print(

            portfolio_df[
                portfolio_df["cap_category"] == "Unknown"
            ][
                [
                    "security_name",
                    "isin"
                ]
            ].to_string(index=False)

        )

    print("\n========== PORTFOLIO WITH MARKET CAP ==========\n")

    print(
        portfolio_df.to_string(index=False)
    )

    return portfolio_df
