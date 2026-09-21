import pandas as pd

# =====================================
# CLEAN AND CONVERT NUMERIC COLUMNS
# =====================================

def _to_numeric(series):

    cleaned = (

        series

        .astype(str)

        .str.replace(r"[₹,]|Rs\.?", "", regex=True)

        .str.strip()

    )

    # Parenthesized numbers represent negatives, e.g. "(123.45)"

    cleaned = cleaned.str.replace(

        r"^\((.*)\)$",

        r"-\1",

        regex=True

    )

    cleaned = cleaned.replace(

        {"": None, "-": None, "nan": None, "None": None}

    )

    return pd.to_numeric(cleaned, errors="coerce")

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

    # Closing Price (fallback source for Closing Value)

    if mapping.get("closing_price"):

        standard_df["closing_price"] = holdings_df[
            mapping["closing_price"]
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

    standard_df["quantity"] = _to_numeric(standard_df["quantity"])

    standard_df["closing_value"] = _to_numeric(standard_df["closing_value"])

    # ---------------------------------
    # Fill Missing Closing Value From Closing Price
    # (statements sometimes leave the value column blank
    # and only populate the per-share closing price)
    # ---------------------------------

    if "closing_price" in standard_df.columns:

        closing_price = _to_numeric(standard_df["closing_price"])

        computed_value = standard_df["quantity"] * closing_price

        standard_df["closing_value"] = standard_df["closing_value"].fillna(
            computed_value
        )

        standard_df = standard_df.drop(columns=["closing_price"])

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