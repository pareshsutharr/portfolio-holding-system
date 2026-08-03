import pandas as pd

# =====================================
# CREATE STANDARD HOLDINGS DATAFRAME
# =====================================

def parse_holdings(df, header_row, headers, mapping):

    # ---------------------------------
    # Extract holdings table
    # ---------------------------------

    holdings_df = df.iloc[
        header_row + 1:
    ].copy()

    holdings_df.columns = headers

    holdings_df.reset_index(
        drop=True,
        inplace=True
    )

    # ---------------------------------
    # Create standardized dataframe
    # ---------------------------------

    standard_df = pd.DataFrame()

    # Security Name

    if mapping.get("security_name"):

        standard_df["security_name"] = holdings_df[
            mapping["security_name"]
        ]

    # ISIN
    print(mapping)
    if mapping.get("isin"):

        standard_df["isin"] = holdings_df[
            mapping["isin"]
        ]

    # Quantity

    if mapping.get("quantity"):

        standard_df["quantity"] = holdings_df[
            mapping["quantity"]
        ]

    # Closing Value

    if mapping.get("closing_value"):

        standard_df["closing_value"] = holdings_df[
            mapping["closing_value"]
        ]

    # ---------------------------------
    # Clean String Columns
    # ---------------------------------

    standard_df["security_name"] = (

        standard_df["security_name"]

        .astype(str)

        .str.strip()

    )

    standard_df["isin"] = (

        standard_df["isin"]

        .astype(str)

        .str.strip()

    )

    # ---------------------------------
    # Convert Numeric Columns
    # ---------------------------------

    standard_df["quantity"] = pd.to_numeric(

        standard_df["quantity"],

        errors="coerce"

    )

    standard_df["closing_value"] = pd.to_numeric(

        standard_df["closing_value"],

        errors="coerce"

    )

    # ---------------------------------
    # Remove Empty ISIN
    # ---------------------------------

    standard_df = standard_df[

        standard_df["isin"].notna()

    ]

    standard_df = standard_df[

        standard_df["isin"] != ""

    ]

    # ---------------------------------
    # Remove rows without quantity
    # ---------------------------------

    standard_df = standard_df[

        standard_df["quantity"].notna()

    ]

    # ---------------------------------
    # Remove rows without value
    # ---------------------------------

    standard_df = standard_df[

        standard_df["closing_value"].notna()

    ]

    # ---------------------------------
    # Remove duplicate ISINs
    # ---------------------------------

    standard_df = standard_df.drop_duplicates(

        subset="isin"

    )

    # ---------------------------------
    # Reset Index
    # ---------------------------------

    standard_df.reset_index(

        drop=True,

        inplace=True

    )

    # ---------------------------------
    # Current Market Price
    # ---------------------------------

    standard_df["current_market_price"] = (

        standard_df["closing_value"]

        / standard_df["quantity"]

    ).round(2)

    # ---------------------------------
    # Portfolio Value
    # ---------------------------------

    standard_df["value"] = standard_df["closing_value"]

    # ---------------------------------
    # Print
    # ---------------------------------

    print("\n========== STANDARD HOLDINGS ==========\n")

    print(

        standard_df.to_string(

            index=False

        )

    )

    print("\nTotal Holdings :", len(standard_df))

    return standard_df