import pandas as pd

# =====================================
# LOAD FILES
# =====================================

portfolio = pd.read_excel(
    "test_files/isin.xlsx",
    header=3          # 4th row contains headers
)

benchmark = pd.read_excel(
    "test_files/BSE500.xlsx"
)

# =====================================
# UNIQUE SECTORS
# =====================================

portfolio_sectors = set(
    portfolio["CD_Sector"]
    .dropna()
    .astype(str)
    .str.strip()
)

benchmark_sectors = set(
    benchmark["Sectors"]
    .dropna()
    .astype(str)
    .str.strip()
)

# =====================================
# PRINT RESULTS
# =====================================

print("\n========== PORTFOLIO SECTORS ==========\n")
for sector in sorted(portfolio_sectors):
    print(sector)

print("\n========== BSE500 SECTORS ==========\n")
for sector in sorted(benchmark_sectors):
    print(sector)

print("\n========== ONLY IN PORTFOLIO ==========\n")
for sector in sorted(portfolio_sectors - benchmark_sectors):
    print(sector)

print("\n========== ONLY IN BSE500 ==========\n")
for sector in sorted(benchmark_sectors - portfolio_sectors):
    print(sector)