import os

from dotenv import load_dotenv


load_dotenv()

# =====================================
# GEMINI CONFIGURATION
# =====================================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# =====================================
# INPUT FILES
# =====================================

HOLDINGS_FILE = "test_files/holdings.xlsx"

ISIN_MASTER_FILE = "test_files/isin.xlsx"

MCAP_MASTER_FILE = "test_files/Mcap.xlsx"

BSE500_FILE = "test_files/BSE500.xlsx"

# =====================================
# STOCK STYLE CLASSIFICATION DATA
# =====================================

STYLE_DATA_DIR = os.getenv(
    "STYLE_DATA_DIR",
    "/tmp/portfolio-reference-data" if os.getenv("VERCEL") else "Portfolio Analyzer Data",
)

# Single Accord export covering Growth, Value, Quality (ROE/ROCE/Interest
# Cover), and Liquidity raw inputs.
STYLE_ACCORD_MASTER_FILE = (
    f"{STYLE_DATA_DIR}/accord_master/Portfolio_Analyzer_v2.xlsx"
    if os.getenv("VERCEL")
    else f"{STYLE_DATA_DIR}/Portfolio_Analyzer_v2.xlsx"
)

# Debt/Equity is not present in the Accord master export above, so Quality
# still reads that one ratio from the legacy workbook.
STYLE_QUALITY_FILE = (
    f"{STYLE_DATA_DIR}/quality_data/Data_Quality.xlsx"
    if os.getenv("VERCEL")
    else f"{STYLE_DATA_DIR}/Data_Quality.xlsx"
)

STYLE_NSE_PRICE_DIR = (
    f"{STYLE_DATA_DIR}/daily_prices_nse"
    if os.getenv("VERCEL")
    else f"{STYLE_DATA_DIR}/Data_NSE"
)

STYLE_BSE_PRICE_DIR = (
    f"{STYLE_DATA_DIR}/daily_prices_bse"
    if os.getenv("VERCEL")
    else f"{STYLE_DATA_DIR}/Data_BSE"
)

STYLE_NIFTY_FILE = (
    f"{STYLE_DATA_DIR}/nifty50_index/Data_Nifty_50.csv"
    if os.getenv("VERCEL")
    else f"{STYLE_DATA_DIR}/Data_Nifty_50.csv"
)

STYLE_CONFIG_FILE = "style_config.json"

# =====================================
# BENCHMARK CONFIGURATION
# =====================================

BENCHMARKS = {

    "nifty50": {

        "name": "Nifty 50",

        "url": "https://www.niftyindices.com/Factsheet/ind_nifty50.pdf",

        "pdf_file": "benchmark/downloads/nifty50_factsheet.pdf",

        "sector_file": "benchmark/output/nifty50_sector_allocation.csv",

        "holdings_file": "benchmark/output/nifty50_top_holdings.csv"

    },

    "nifty_midcap_150": {

        "name": "Nifty Midcap 150",

        "url": "https://www.niftyindices.com/Factsheet/ind_Nifty_Midcap_150.pdf",

        "pdf_file": "benchmark/downloads/nifty_midcap_150_factsheet.pdf",

        "sector_file": "benchmark/output/nifty_midcap_150_sector_allocation.csv",

        "holdings_file": "benchmark/output/nifty_midcap_150_top_holdings.csv"

    },

    "nifty500": {

        "name": "Nifty 500",

        "url": "https://www.niftyindices.com/Factsheet/ind_nifty_500.pdf",

        "pdf_file": "benchmark/downloads/nifty500_factsheet.pdf",

        "sector_file": "benchmark/output/nifty500_sector_allocation.csv",

        "holdings_file": "benchmark/output/nifty500_top_holdings.csv"

    }

}

BENCHMARK_KEYS = [
    "nifty50",
    "nifty_midcap_150",
    "nifty500"
]

BENCHMARK_REFRESH = False

# =====================================
# SECTORAL INDEX FUNDAMENTALS (VALUE BENCHMARKING)
# =====================================
# NOTE: URLs follow the same https://www.niftyindices.com/Factsheet/ind_*.pdf
# pattern as BENCHMARKS above, confirmed working for nifty_bank. The other
# slugs are best-effort and should be verified against the live site --
# NSE's naming isn't perfectly consistent across every sectoral index.

SECTORAL_INDICES = {

    "nifty_it": {
        "name": "Nifty IT",
        "nse_sector": "Information Technology",
        "url": "https://www.niftyindices.com/Factsheet/ind_nifty_it.pdf",
        "pdf_file": "benchmark/downloads/nifty_it_factsheet.pdf"
    },

    "nifty_bank": {
        "name": "Nifty Bank",
        "nse_sector": "Financial Services",
        "url": "https://www.niftyindices.com/Factsheet/ind_nifty_bank.pdf",
        "pdf_file": "benchmark/downloads/nifty_bank_factsheet.pdf"
    },

    "nifty_auto": {
        "name": "Nifty Auto",
        "nse_sector": "Automobile and Auto Components",
        "url": "https://www.niftyindices.com/Factsheet/ind_nifty_auto.pdf",
        "pdf_file": "benchmark/downloads/nifty_auto_factsheet.pdf"
    },

    "nifty_fmcg": {
        "name": "Nifty FMCG",
        "nse_sector": "Fast Moving Consumer Goods",
        "url": "https://www.niftyindices.com/Factsheet/ind_nifty_fmcg.pdf",
        "pdf_file": "benchmark/downloads/nifty_fmcg_factsheet.pdf"
    },

    "nifty_pharma": {
        "name": "Nifty Pharma",
        "nse_sector": "Healthcare",
        "url": "https://www.niftyindices.com/Factsheet/ind_nifty_pharma.pdf",
        "pdf_file": "benchmark/downloads/nifty_pharma_factsheet.pdf"
    },

    "nifty_metal": {
        "name": "Nifty Metal",
        "nse_sector": "Metals & Mining",
        "url": "https://www.niftyindices.com/Factsheet/ind_nifty_metal.pdf",
        "pdf_file": "benchmark/downloads/nifty_metal_factsheet.pdf"
    },

    "nifty_energy": {
        "name": "Nifty Energy",
        "nse_sector": "Oil, Gas & Consumable Fuels",
        "url": "https://www.niftyindices.com/Factsheet/ind_nifty_energy.pdf",
        "pdf_file": "benchmark/downloads/nifty_energy_factsheet.pdf"
    },

    "nifty_realty": {
        "name": "Nifty Realty",
        "nse_sector": "Realty",
        "url": "https://www.niftyindices.com/Factsheet/ind_nifty_realty.pdf",
        "pdf_file": "benchmark/downloads/nifty_realty_factsheet.pdf"
    },

    "nifty_media": {
        "name": "Nifty Media",
        "nse_sector": "Media, Entertainment & Publication",
        "url": "https://www.niftyindices.com/Factsheet/ind_nifty_media.pdf",
        "pdf_file": "benchmark/downloads/nifty_media_factsheet.pdf"
    },

    "nifty_consumer_durables": {
        "name": "Nifty Consumer Durables",
        "nse_sector": "Consumer Durables",
        "url": "https://www.niftyindices.com/Factsheet/Factsheet_nifty_consumer_durables.pdf",
        "pdf_file": "benchmark/downloads/nifty_consumer_durables_factsheet.pdf"
    },

    "nifty_capital_goods": {
        "name": "Nifty Capital Goods",
        "nse_sector": "Capital Goods",
        "url": "https://www.niftyindices.com/Factsheet/Factsheet_Nifty_Capital_Goods.pdf",
        "pdf_file": "benchmark/downloads/nifty_capital_goods_factsheet.pdf"
    },

    "nifty_chemicals": {
        "name": "Nifty Chemicals",
        "nse_sector": "Chemicals",
        "url": "https://www.niftyindices.com/Factsheet/Factsheet_Nifty_Chemicals.pdf",
        "pdf_file": "benchmark/downloads/nifty_chemicals_factsheet.pdf"
    },

    "nifty_consumer_services": {
        "name": "Nifty Consumer Services",
        "nse_sector": "Consumer Services",
        "url": "https://www.niftyindices.com/Factsheet/Factsheet_Nifty_Consumer_Services.pdf",
        "pdf_file": "benchmark/downloads/nifty_consumer_services_factsheet.pdf"
    },

    "nifty_telecommunications": {
        "name": "Nifty Telecommunications",
        "nse_sector": "Telecommunication",
        "url": "https://www.niftyindices.com/Factsheet/Factsheet_Nifty_Telecommunications.pdf",
        "pdf_file": "benchmark/downloads/nifty_telecommunications_factsheet.pdf"
    },

    "nifty_power": {
        "name": "Nifty Power",
        "nse_sector": "Power",
        "url": "https://www.niftyindices.com/Factsheet/Factsheet_Nifty_Power.pdf",
        "pdf_file": "benchmark/downloads/nifty_power_factsheet.pdf"
    },

    "nifty_cement": {
        "name": "Nifty Cement",
        "nse_sector": "Construction Materials",
        "url": "https://www.niftyindices.com/Factsheet/Factsheet_Nifty_Cement.pdf",
        "pdf_file": "benchmark/downloads/nifty_cement_factsheet.pdf"
    },

    "nifty_financial_services": {
        "name": "Nifty Financial Services",
        "nse_sector": "Financial Services",
        "url": "https://www.niftyindices.com/Factsheet/ind_nifty_financial_services.pdf",
        "pdf_file": "benchmark/downloads/nifty_financial_services_factsheet.pdf"
    },

    "nifty_commercial_transport": {
        "name": "Nifty Commercial & Transport Services",
        "nse_sector": "Commercial & Transport Services",
        "url": "https://www.niftyindices.com/Factsheet/Factsheet_Nifty_Commercial_and_Transport_Services.pdf",
        "pdf_file": "benchmark/downloads/nifty_commercial_transport_factsheet.pdf"
    },

    "nifty_construction": {
        "name": "Nifty Construction",
        "nse_sector": "Construction",
        "url": "https://www.niftyindices.com/Factsheet/Factsheet_Nifty_Construction.pdf",
        "pdf_file": "benchmark/downloads/nifty_construction_factsheet.pdf"
    },

    "nifty_financial_services_25_50": {
        "name": "Nifty Financial Services 25/50",
        "nse_sector": "Financial Services",
        "url": "https://www.niftyindices.com/Factsheet/Factsheet_Nifty_FinServ_25_50.pdf",
        "pdf_file": "benchmark/downloads/nifty_financial_services_25_50_factsheet.pdf"
    },

    "nifty_financial_services_ex_bank": {
        "name": "Nifty Financial Services Ex Bank",
        "nse_sector": "Financial Services",
        "url": "https://www.niftyindices.com/Factsheet/Factsheet_NiftyFinancialServicesExBank.pdf",
        "pdf_file": "benchmark/downloads/nifty_financial_services_ex_bank_factsheet.pdf"
    },

    "nifty_healthcare": {
        "name": "Nifty Healthcare",
        "nse_sector": "Healthcare",
        "url": "https://www.niftyindices.com/Factsheet/Factsheet_Nifty_Healthcare_Index.pdf",
        "pdf_file": "benchmark/downloads/nifty_healthcare_factsheet.pdf"
    },

    "nifty_hospitals": {
        "name": "Nifty Hospitals",
        "nse_sector": "Healthcare",
        "url": "https://www.niftyindices.com/Factsheet/Factsheet_Nifty_Hospitals.pdf",
        "pdf_file": "benchmark/downloads/nifty_hospitals_factsheet.pdf"
    },

    "nifty_housing_finance": {
        "name": "Nifty Housing Finance",
        "nse_sector": "Financial Services",
        "url": "https://www.niftyindices.com/Factsheet/Factsheet_Nifty_Housing_Finance.pdf",
        "pdf_file": "benchmark/downloads/nifty_housing_finance_factsheet.pdf"
    },

    "nifty_insurance": {
        "name": "Nifty Insurance",
        "nse_sector": "Financial Services",
        "url": "https://www.niftyindices.com/Factsheet/Factsheet_Nifty_Insurance.pdf",
        "pdf_file": "benchmark/downloads/nifty_insurance_factsheet.pdf"
    },

    "nifty_nbfc": {
        "name": "Nifty NBFC",
        "nse_sector": "Financial Services",
        "url": "https://www.niftyindices.com/Factsheet/Factsheet_Nifty_NBFC.pdf",
        "pdf_file": "benchmark/downloads/nifty_nbfc_factsheet.pdf"
    },

    "nifty_oil_and_gas": {
        "name": "Nifty Oil and Gas",
        "nse_sector": "Oil, Gas & Consumable Fuels",
        "url": "https://www.niftyindices.com/Factsheet/Factsheet_nifty_oil_and_gas.pdf",
        "pdf_file": "benchmark/downloads/nifty_oil_and_gas_factsheet.pdf"
    },

    "nifty_private_bank": {
        "name": "Nifty Private Bank",
        "nse_sector": "Financial Services",
        "url": "https://www.niftyindices.com/Factsheet/ind_nifty_private_bank.pdf",
        "pdf_file": "benchmark/downloads/nifty_private_bank_factsheet.pdf"
    },

    "nifty_psu_bank": {
        "name": "Nifty PSU Bank",
        "nse_sector": "Financial Services",
        "url": "https://www.niftyindices.com/Factsheet/ind_nifty_psu_bank.pdf",
        "pdf_file": "benchmark/downloads/nifty_psu_bank_factsheet.pdf"
    },

    "nifty_reits_realty": {
        "name": "Nifty REITs & Realty",
        "nse_sector": "Realty",
        "url": "https://www.niftyindices.com/Factsheet/Factsheet_Nifty_REITs_and_Realty.pdf",
        "pdf_file": "benchmark/downloads/nifty_reits_realty_factsheet.pdf"
    },

    "nifty_retail": {
        "name": "Nifty Retail",
        "nse_sector": "Consumer Services",
        "url": "https://www.niftyindices.com/Factsheet/Factsheet_Nifty_Retail.pdf",
        "pdf_file": "benchmark/downloads/nifty_retail_factsheet.pdf"
    },

    "nifty500_healthcare": {
        "name": "Nifty500 Healthcare",
        "nse_sector": "Healthcare",
        "url": "https://www.niftyindices.com/Factsheet/Factsheet_Nifty500Healthcare.pdf",
        "pdf_file": "benchmark/downloads/nifty500_healthcare_factsheet.pdf"
    },

    "nifty_midsmall_financial_services": {
        "name": "Nifty MidSmall Financial Services",
        "nse_sector": "Financial Services",
        "url": "https://www.niftyindices.com/Factsheet/Factsheet_NiftyMidSmallFinancialSevices.pdf",
        "pdf_file": "benchmark/downloads/nifty_midsmall_financial_services_factsheet.pdf"
    },

    "nifty_midsmall_healthcare": {
        "name": "Nifty MidSmall Healthcare",
        "nse_sector": "Healthcare",
        "url": "https://www.niftyindices.com/Factsheet/Factsheet_NiftyMidSmallHealthCare.pdf",
        "pdf_file": "benchmark/downloads/nifty_midsmall_healthcare_factsheet.pdf"
    },

    "nifty_midsmall_it_telecom": {
        "name": "Nifty MidSmall IT & Telecom",
        "nse_sector": "Information Technology",
        "url": "https://www.niftyindices.com/Factsheet/Factsheet_NiftyMidSmallITAndTelecom.pdf",
        "pdf_file": "benchmark/downloads/nifty_midsmall_it_telecom_factsheet.pdf"
    }

}

SECTORAL_FUNDAMENTALS_FILE = "benchmark/output/sectoral_fundamentals.csv"

# =====================================
# OUTPUT FOLDER
# =====================================

OUTPUT_FOLDER = "output"

# =====================================
# PDF NAME
# =====================================

PDF_REPORT_NAME = "portfolio_report.pdf"

# =====================================
# EXCEL REPORT NAME
# =====================================

EXCEL_REPORT_NAME = "portfolio_report.xlsx"

SECTOR_MAPPING_FILE = "test_files/sector_mapping.xlsx"
