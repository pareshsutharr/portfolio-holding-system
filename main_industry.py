import pandas as pd
import json
from google import genai
import matplotlib.pyplot as plt

# =====================================
# CONFIG
# =====================================

client = genai.Client(
    api_key="AQ.Ab8RN6LWgVPbnuYZp49NZelhfb_A0oYnvslsd2EPmH2YK9GQlw"
)

file_path = "test_files/holdings.xlsx"
isin_master_file = "test_files/isin.xlsx"
cap_master_file = "test_files/Mcap.xlsx"
# =====================================
# READ HOLDINGS EXCEL
# =====================================

df = pd.read_excel(
    file_path,
    header=None
)

# =====================================
# FIND HEADER ROW
# =====================================

keywords = [
    "isin",
    "quantity",
    "qty",
    "stock name",
    "security name",
    "buy value",
    "closing value",
    "market value",
    "average buy price",
    "unrealised p&l"
]

best_row_index = -1
best_score = -1

for index, row in df.iterrows():

    score = 0

    for cell in row:

        if pd.isna(cell):
            continue

        cell_text = str(cell).strip().lower()

        for keyword in keywords:

            if keyword in cell_text:
                score += 1

    if score > best_score:
        best_score = score
        best_row_index = index

print("\n========== HEADER DETECTION ==========\n")

print(f"Header Row Found: {best_row_index}")
print(f"Header Score: {best_score}")

# =====================================
# EXTRACT HEADERS
# =====================================

headers = [
    str(x).strip()
    for x in df.iloc[best_row_index].tolist()
    if pd.notna(x)
]

print("\nDetected Headers:")
print(headers)

# =====================================
# GEMINI PROMPT
# =====================================

prompt = f"""
You are a portfolio statement expert.

Map the following column headers to the standard fields below.

Standard Fields:
- security_name
- isin
- quantity
- closing_value

Headers:
{headers}

Rules:
1. Return ONLY JSON.
2. If a field is not found return null.
3. No explanation.

Example:

{{
    "security_name": "Stock Name",
    "isin": "ISIN",
    "quantity": "Quantity",
    "closing_value": "Closing value"
}}
"""

# =====================================
# GEMINI CALL
# =====================================

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt
)

print("\n========== GEMINI RESPONSE ==========\n")
print(response.text)

# =====================================
# CLEAN GEMINI RESPONSE
# =====================================

try:

    clean_text = response.text.strip()

    clean_text = clean_text.replace(
        "```json",
        ""
    )

    clean_text = clean_text.replace(
        "```",
        ""
    )

    clean_text = clean_text.strip()

    mapping = json.loads(clean_text)

    print("\n========== PARSED MAPPING ==========\n")

    print(
        json.dumps(
            mapping,
            indent=4
        )
    )

except Exception as e:

    print("\nJSON Parsing Failed")
    print(e)

    exit()

# =====================================
# CREATE HOLDINGS TABLE
# =====================================

holdings_df = df.iloc[
    best_row_index + 1:
].copy()

holdings_df.columns = headers

holdings_df.reset_index(
    drop=True,
    inplace=True
)

# =====================================
# CREATE STANDARD DATAFRAME
# =====================================

standard_df = pd.DataFrame()

if mapping.get("security_name"):

    standard_df["security_name"] = holdings_df[
        mapping["security_name"]
    ]

if mapping.get("isin"):

    standard_df["isin"] = holdings_df[
        mapping["isin"]
    ]

if mapping.get("quantity"):

    standard_df["quantity"] = holdings_df[
        mapping["quantity"]
    ]

# =====================================
# CLEAN STANDARD DATAFRAME
# =====================================

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

standard_df["quantity"] = (
    standard_df["quantity"]
)

# Remove empty rows

standard_df = standard_df[
    standard_df["isin"].notna()
]

standard_df = standard_df[
    standard_df["isin"] != ""
]

print("\n========== STANDARD DATAFRAME ==========\n")

print(
    standard_df.to_string(
        index=False
    )
)

# =====================================
# READ ISIN MASTER FILE
# =====================================

isin_master = pd.read_excel(
    isin_master_file,
    header=3
)

print("\n========== ISIN MASTER COLUMNS ==========\n")

print(
    isin_master.columns.tolist()
)

# =====================================
# KEEP REQUIRED COLUMNS
# =====================================

isin_master = isin_master[
    [
        "CD_ISIN No",
        "CD_Sector",
        "CD_Industry1"
    ]
].copy()

# =====================================
# RENAME COLUMNS
# =====================================

isin_master.rename(
    columns={
        "CD_ISIN No": "isin",
        "CD_Sector": "sector",
        "CD_Industry1": "industry"
    },
    inplace=True
)

# =====================================
# CLEAN ISIN MASTER
# =====================================

isin_master["isin"] = (
    isin_master["isin"]
    .astype(str)
    .str.strip()
)

# =====================================
# MERGE DATAFRAMES
# =====================================

enriched_df = pd.merge(
    standard_df,
    isin_master,
    on="isin",
    how="left"
)

# =====================================
# FINAL OUTPUT
# =====================================

print("\n========== ENRICHED PORTFOLIO ==========\n")

print(
    enriched_df.to_string(
        index=False
    )
)

# =====================================
# MATCH SUMMARY
# =====================================

total_rows = len(enriched_df)

matched_rows = (
    enriched_df["sector"]
    .notna()
    .sum()
)

unmatched_rows = total_rows - matched_rows

print("\n========== MATCH SUMMARY ==========\n")

print(f"Total Holdings : {total_rows}")
print(f"Matched ISINs  : {matched_rows}")
print(f"Unmatched ISINs: {unmatched_rows}")

# =====================================
# SHOW UNMATCHED ISINS
# =====================================

if unmatched_rows > 0:

    print("\n========== UNMATCHED ISINS ==========\n")

    unmatched_df = enriched_df[
        enriched_df["sector"].isna()
    ][
        [
            "security_name",
            "isin"
        ]
    ]

    print(
        unmatched_df.to_string(
            index=False
        )
    )

    # =====================================
# SECTOR ALLOCATION
# =====================================

sector_df = (
    enriched_df
    .groupby("sector")
    .size()
    .reset_index(name="stock_count")
)

sector_df["allocation_percent"] = (
    sector_df["stock_count"]
    / sector_df["stock_count"].sum()
    * 100
).round(2)

sector_df = sector_df.sort_values(
    by="allocation_percent",
    ascending=False
)

print("\n========== SECTOR ALLOCATION ==========\n")

print(
    sector_df.to_string(
        index=False
    )
)

# =====================================
# INDUSTRY ALLOCATION
# =====================================

industry_df = (
    enriched_df
    .groupby("industry")
    .size()
    .reset_index(name="stock_count")
)

industry_df["allocation_percent"] = (
    industry_df["stock_count"]
    / industry_df["stock_count"].sum()
    * 100
).round(2)

industry_df = industry_df.sort_values(
    by="allocation_percent",
    ascending=False
)

print("\n========== INDUSTRY ALLOCATION ==========\n")

print(
    industry_df.to_string(
        index=False
    )
)

# =====================================
# TOP SECTORS
# =====================================

print("\n========== TOP 5 SECTORS ==========\n")

print(
    sector_df.head(5).to_string(
        index=False
    )
)

# =====================================
# TOP INDUSTRIES
# =====================================

print("\n========== TOP 10 INDUSTRIES ==========\n")

print(
    industry_df.head(10).to_string(
        index=False
    )
)

# =====================================
# PORTFOLIO SUMMARY
# =====================================

print("\n========== PORTFOLIO SUMMARY ==========\n")

print(
    f"Total Stocks     : {len(enriched_df)}"
)

print(
    f"Total Sectors    : {enriched_df['sector'].nunique()}"
)

print(
    f"Total Industries : {enriched_df['industry'].nunique()}"
)

print(
    f"Largest Sector   : {sector_df.iloc[0]['sector']}"
)

print(
    f"Largest Industry : {industry_df.iloc[0]['industry']}"
)

print(
    f"Largest Sector % : {sector_df.iloc[0]['allocation_percent']}%"
)

print(
    f"Largest Industry % : {industry_df.iloc[0]['allocation_percent']}%"
)

# =====================================
# SECTOR DIVERSIFICATION SCORE
# =====================================

sector_count = enriched_df["sector"].nunique()

if sector_count >= 10:
    diversification = "Excellent"
elif sector_count >= 7:
    diversification = "Good"
elif sector_count >= 5:
    diversification = "Average"
else:
    diversification = "Poor"

print(
    f"Diversification Score : {diversification}"
)

# =====================================
# CLOSING VALUE
# =====================================

if mapping.get("closing_value"):

    standard_df["closing_value"] = holdings_df[
        mapping["closing_value"]
    ]

# =====================================
# CLEAN NUMERIC DATA
# =====================================

standard_df["closing_value"] = pd.to_numeric(
    standard_df["closing_value"],
    errors="coerce"
)

standard_df["quantity"] = pd.to_numeric(
    standard_df["quantity"],
    errors="coerce"
)

# Remove rows without closing value

standard_df = standard_df[
    standard_df["closing_value"].notna()
]

# =====================================
# PORTFOLIO VALUE
# =====================================

total_portfolio_value = (
    standard_df["closing_value"]
    .sum()
)

# =====================================
# STOCK WEIGHTAGE
# =====================================

standard_df["weight_percent"] = (
    standard_df["closing_value"]
    / total_portfolio_value
    * 100
).round(2)

standard_df = standard_df.sort_values(
    by="weight_percent",
    ascending=False
)

print("\n========== PORTFOLIO WEIGHTAGE ==========\n")

print(
    standard_df[
        [
            "security_name",
            "closing_value",
            "weight_percent"
        ]
    ].to_string(index=False)
)

print("\n========== TOTAL PORTFOLIO VALUE ==========\n")

print(
    f"₹ {total_portfolio_value:,.2f}"
)

# =====================================
# MERGE WEIGHTAGE WITH SECTOR DATA
# =====================================

portfolio_df = pd.merge(
    standard_df,
    isin_master,
    on="isin",
    how="left"
)

# =====================================
# SECTOR ALLOCATION BY VALUE
# =====================================

sector_value_df = (
    portfolio_df
    .groupby("sector")["closing_value"]
    .sum()
    .reset_index()
)

sector_value_df["allocation_percent"] = (
    sector_value_df["closing_value"]
    / total_portfolio_value
    * 100
).round(2)

sector_value_df = sector_value_df.sort_values(
    by="allocation_percent",
    ascending=False
)

print("\n========== SECTOR ALLOCATION BY VALUE ==========\n")

print(
    sector_value_df.to_string(
        index=False
    )
)

# =====================================
# INDUSTRY ALLOCATION BY VALUE
# =====================================

industry_value_df = (
    portfolio_df
    .groupby("industry")["closing_value"]
    .sum()
    .reset_index()
)

industry_value_df["allocation_percent"] = (
    industry_value_df["closing_value"]
    / total_portfolio_value
    * 100
).round(2)

industry_value_df = industry_value_df.sort_values(
    by="allocation_percent",
    ascending=False
)

print("\n========== INDUSTRY ALLOCATION BY VALUE ==========\n")

print(
    industry_value_df.to_string(
        index=False
    )
)

# =====================================
# TOP 5 HOLDINGS
# =====================================

top5_weight = (
    standard_df
    .head(5)["weight_percent"]
    .sum()
)

print("\n========== TOP HOLDINGS ANALYSIS ==========\n")

print(
    standard_df[
        [
            "security_name",
            "weight_percent"
        ]
    ]
    .head(5)
    .to_string(index=False)
)

print(
    f"\nTop 5 Holdings Concentration : {top5_weight:.2f}%"
)

# =====================================
# CONCENTRATION RISK
# =====================================

top2_weight = (
    standard_df
    .head(2)["weight_percent"]
    .sum()
)

print("\n========== CONCENTRATION RISK ==========\n")

print(
    f"Top 2 Stocks Weight : {top2_weight:.2f}%"
)

if top2_weight > 50:
    risk = "HIGH"
elif top2_weight > 35:
    risk = "MEDIUM"
else:
    risk = "LOW"

print(
    f"Portfolio Concentration Risk : {risk}"
)

# =====================================
# SECTOR ALLOCATION PIE CHART
# =====================================

plt.figure(figsize=(10, 8))

plt.pie(
    sector_value_df["allocation_percent"],
    labels=sector_value_df["sector"],
    autopct="%1.1f%%"
)

plt.title(
    "Portfolio Sector Allocation",
    fontsize=16,
    fontweight="bold"
)

plt.tight_layout()

plt.savefig(
    "sector_allocation_pie.png",
    dpi=300,
    bbox_inches="tight"
)

plt.close()

print(
    "\nSaved: sector_allocation_pie.png"
)

# =====================================
# INDUSTRY ALLOCATION PIE CHART
# =====================================

plt.figure(figsize=(10, 8))

plt.pie(
    industry_value_df["allocation_percent"],
    labels=industry_value_df["industry"],
    autopct="%1.1f%%"
)

plt.title(
    "Portfolio Industry Allocation",
    fontsize=16,
    fontweight="bold"
)

plt.tight_layout()

plt.savefig(
    "industry_allocation_pie.png",
    dpi=300,
    bbox_inches="tight"
)

plt.close()

print(
    "Saved: industry_allocation_pie.png"
)

# =====================================
# TOP HOLDINGS BAR CHART
# =====================================

top_holdings = standard_df.head(10)

plt.figure(figsize=(14, 8))

plt.barh(
    top_holdings["security_name"],
    top_holdings["weight_percent"]
)

plt.xlabel("Weight (%)")
plt.ylabel("Stock")

plt.title(
    "Top Holdings",
    fontsize=16,
    fontweight="bold"
)

plt.tight_layout()

plt.savefig(
    "top_holdings_bar.png",
    dpi=300,
    bbox_inches="tight"
)

plt.close()

print(
    "Saved: top_holdings_bar.png"
)

# =====================================
# SECTOR ALLOCATION BAR CHART
# =====================================

plt.figure(figsize=(12, 8))

plt.barh(
    sector_value_df["sector"],
    sector_value_df["allocation_percent"]
)

plt.xlabel("Allocation (%)")

plt.title(
    "Sector Allocation",
    fontsize=16,
    fontweight="bold"
)

plt.tight_layout()

plt.savefig(
    "sector_allocation_bar.png",
    dpi=300,
    bbox_inches="tight"
)

plt.close()

print(
    "Saved: sector_allocation_bar.png"
)

# =====================================
# INDUSTRY ALLOCATION BAR CHART
# =====================================

plt.figure(figsize=(14, 8))

plt.barh(
    industry_value_df["industry"],
    industry_value_df["allocation_percent"]
)

plt.xlabel("Allocation (%)")

plt.title(
    "Industry Allocation",
    fontsize=16,
    fontweight="bold"
)

plt.tight_layout()

plt.savefig(
    "industry_allocation_bar.png",
    dpi=300,
    bbox_inches="tight"
)

plt.close()



print(
    "Saved: industry_allocation_bar.png"
)

print("\n========== CHARTS GENERATED ==========\n")

print("1. sector_allocation_pie.png")
print("2. industry_allocation_pie.png")
print("3. top_holdings_bar.png")
print("4. sector_allocation_bar.png")
print("5. industry_allocation_bar.png")

portfolio_df = pd.merge(
    standard_df,
    isin_master,
    on="isin",
    how="left"
)

# ---------- PASTE THE CAP CATEGORY CODE HERE ----------

# Read AMFI master
cap_master = pd.read_excel(
    cap_master_file,
    header=1
)

# Keep required columns
cap_master = cap_master[
    [
        "ISIN",
        "Categorization as per SEBI Circular dated Oct 6, 2017"
    ]
].copy()

# Rename columns
cap_master.rename(
    columns={
        "ISIN": "isin",
        "Categorization as per SEBI Circular dated Oct 6, 2017": "cap_category"
    },
    inplace=True
)

# Clean ISIN
cap_master["isin"] = (
    cap_master["isin"]
    .astype(str)
    .str.strip()
)

# Merge with portfolio
portfolio_df = pd.merge(
    portfolio_df,
    cap_master,
    on="isin",
    how="left"
)

print("\n========== PORTFOLIO WITH CAP CATEGORY ==========\n")

print(
    portfolio_df[
        [
            "security_name",
            "isin",
            "sector",
            "industry",
            "cap_category"
        ]
    ].to_string(index=False)
)

portfolio_df["current_market_price"] = (
    portfolio_df["closing_value"] / portfolio_df["quantity"]
).round(2)

portfolio_df["value"] = (
    portfolio_df["quantity"] * portfolio_df["current_market_price"]
).round(2)

report_df = portfolio_df[
    [
        "isin",
        "security_name",
        "cap_category",
        "sector",
        "industry",
        "quantity",
        "current_market_price",
        "value",
        "weight_percent"
    ]
].copy()


report_df.to_excel(
    "Portfolio_Report.xlsx",
    index=False
)



import os

print("\n========== PDF STATUS ==========\n")

if os.path.exists("portfolio_report.pdf"):
    print("PDF created successfully.")
    print(os.path.abspath("portfolio_report.pdf"))
else:
    print("PDF was NOT created.")




# =====================================
# CREATE PDF REPORT
# =====================================

from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph
)

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER

styles = getSampleStyleSheet()

title_style = styles["Heading1"]
title_style.alignment = TA_CENTER

normal_style = styles["BodyText"]

doc = SimpleDocTemplate(
    "portfolio_report.pdf",
    pagesize=(11.69 * inch, 8.27 * inch)   # A4 Landscape
)

elements = []

# =====================================
# TITLE
# =====================================

elements.append(
    Paragraph(
        "Portfolio Holdings Report",
        title_style
    )
)

elements.append(
    Paragraph("<br/><br/>", normal_style)
)

# =====================================
# SUMMARY
# =====================================

summary = f"""
<b>Total Stocks :</b> {len(report_df)}
<br/>
<b>Total Portfolio Value :</b> Rs. {total_portfolio_value:,.2f}
<br/>
<b>Diversification :</b> {diversification}
<br/>
<b>Concentration Risk :</b> {risk}
<br/><br/>
"""

elements.append(
    Paragraph(
        summary,
        normal_style
    )
)

# =====================================
# TABLE DATA
# =====================================

table_data = []

table_data.append([
    "ISIN",
    "Company",
    "Cap",
    "Sector",
    "Industry",
    "Qty",
    "CMP",
    "Value",
    "Weight %"
])

for _, row in report_df.iterrows():

    table_data.append([

        str(row["isin"]),

        str(row["security_name"]),

        str(row["cap_category"]),

        str(row["sector"]),

        str(row["industry"]),

        int(row["quantity"]),

        f"{row['current_market_price']:.2f}",

        f"{row['value']:,.2f}",

        f"{row['weight_percent']:.2f}%"

    ])

# =====================================
# CREATE TABLE
# =====================================

table = Table(table_data)

table.setStyle(

    TableStyle([

        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#1F4E78")),

        ("TEXTCOLOR",(0,0),(-1,0),colors.white),

        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),

        ("FONTSIZE",(0,0),(-1,0),10),

        ("BOTTOMPADDING",(0,0),(-1,0),10),

        ("BACKGROUND",(0,1),(-1,-1),colors.beige),

        ("GRID",(0,0),(-1,-1),0.5,colors.grey),

        ("ALIGN",(0,0),(-1,-1),"CENTER"),

        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),

        ("FONTNAME",(0,1),(-1,-1),"Helvetica"),

        ("FONTSIZE",(0,1),(-1,-1),8),

        ("ROWBACKGROUNDS",(0,1),(-1,-1),
            [colors.white, colors.HexColor("#F5F5F5")]
        )

    ])

)

elements.append(table)



# =====================================
# BUILD PDF
# =====================================

doc.build(elements)

print("\n========== PDF GENERATED ==========\n")

print("Saved : portfolio_report.pdf")

