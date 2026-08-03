# import json
# import os

# MAPPING_FILE = "sector_mapping.json"


# # =====================================
# # LOAD MAPPING
# # =====================================

# def load_mapping():

#     if os.path.exists(MAPPING_FILE):

#         with open(MAPPING_FILE, "r") as f:
#             return json.load(f)

#     return {}


# # =====================================
# # SAVE MAPPING
# # =====================================

# def save_mapping(mapping):

#     with open(MAPPING_FILE, "w") as f:
#         json.dump(
#             mapping,
#             f,
#             indent=4,
#             sort_keys=True
#         )


# # =====================================
# # FIND UNKNOWN SECTORS
# # =====================================

# def find_unknown_sectors(
#     portfolio_sectors,
#     benchmark_sectors,
#     mapping
# ):

#     unknown = []

#     for sector in portfolio_sectors:

#         if sector not in mapping:
#             unknown.append(sector)

#     return sorted(unknown)


import json
import os
import pandas as pd

# =====================================
# CONFIG
# =====================================

MAPPING_FILE = "sector_mapping.json"

# =====================================
# LOAD MAPPING
# =====================================

def load_mapping():

    if os.path.exists(MAPPING_FILE):

        with open(MAPPING_FILE, "r") as f:
            return json.load(f)

    return {}

# =====================================
# SAVE MAPPING
# =====================================

def save_mapping(mapping):

    with open(MAPPING_FILE, "w") as f:
        json.dump(
            mapping,
            f,
            indent=4,
            sort_keys=True
        )

# =====================================
# FIND UNKNOWN SECTORS
# =====================================

def find_unknown_sectors(
    portfolio_sectors,
    benchmark_sectors,
    mapping
):

    unknown = []

    for sector in portfolio_sectors:

        if sector not in mapping:
            unknown.append(sector)

    return sorted(unknown)

# =====================================
# APPLY MAPPING TO PORTFOLIO
# =====================================

def apply_sector_mapping(portfolio_df):

    mapping = load_mapping()

    portfolio_df = portfolio_df.copy()

    portfolio_df["ace_sector"] = portfolio_df["sector"]

    portfolio_df["sector"] = (
        portfolio_df["sector"]
        .map(mapping)
        .fillna(portfolio_df["sector"])
    )

    return portfolio_df

# =====================================
# SHOW MAPPING SUMMARY
# =====================================

def mapping_summary(portfolio_df):

    print("\n========== SECTOR MAPPING ==========\n")

    summary = (
        portfolio_df[
            ["ace_sector", "sector"]
        ]
        .drop_duplicates()
        .sort_values("ace_sector")
    )

    print(summary.to_string(index=False))

    print("\nTotal Sector Mappings :", len(summary))