import json
import pandas as pd

# =====================================
# CONFIG
# =====================================

EXCEL_FILE = "test_files/sector_mapping.xlsx"
OUTPUT_FILE = "sector_mapping.json"

# =====================================
# READ EXCEL
# =====================================

df = pd.read_excel(EXCEL_FILE)

# =====================================
# CREATE MAPPING
# =====================================

mapping = {}

for _, row in df.iterrows():

    ace_sector = str(row["Ace Eq."]).strip()
    nse_sector = str(row["Mapped NSE"]).strip()

    if (
        ace_sector != "nan"
        and nse_sector != "nan"
        and ace_sector != ""
        and nse_sector != ""
    ):

        mapping[ace_sector] = nse_sector

# =====================================
# SAVE JSON
# =====================================

with open(OUTPUT_FILE, "w") as f:

    json.dump(
        mapping,
        f,
        indent=4,
        sort_keys=True
    )

print("\n========== DONE ==========\n")

print(f"Total Mappings : {len(mapping)}")

print(f"JSON Saved As : {OUTPUT_FILE}")