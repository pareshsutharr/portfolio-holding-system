import pandas as pd

# =====================================
# ANALYZE PORTFOLIO
# =====================================

def analyze_portfolio(portfolio_df):

    # =====================================
    # TOTAL PORTFOLIO VALUE
    # =====================================

    total_value = portfolio_df["value"].sum()

    # =====================================
    # STOCK WEIGHTAGE
    # =====================================

    portfolio_df["weight_percent"] = (
        portfolio_df["value"]
        / total_value
        * 100
    ).round(2)

    portfolio_df = portfolio_df.sort_values(
        by="weight_percent",
        ascending=False
    )

    # =====================================
    # SECTOR ALLOCATION
    # =====================================

    sector_df = (

        portfolio_df

        .groupby("sector")["value"]

        .sum()

        .reset_index()

    )

    sector_df["allocation_percent"] = (

        sector_df["value"]

        / total_value

        * 100

    ).round(2)

    sector_df = sector_df.sort_values(

        by="allocation_percent",

        ascending=False

    )

    # =====================================
    # INDUSTRY ALLOCATION
    # =====================================

    industry_df = (

        portfolio_df

        .groupby("industry")["value"]

        .sum()

        .reset_index()

    )

    industry_df["allocation_percent"] = (

        industry_df["value"]

        / total_value

        * 100

    ).round(2)

    industry_df = industry_df.sort_values(

        by="allocation_percent",

        ascending=False

    )

    # =====================================
    # MARKET CAP ALLOCATION
    # =====================================

    cap_df = (

        portfolio_df

        .groupby("cap_category")["value"]

        .sum()

        .reset_index()

    )

    cap_df["allocation_percent"] = (

        cap_df["value"]

        / total_value

        * 100

    ).round(2)

    cap_df = cap_df.sort_values(

        by="allocation_percent",

        ascending=False

    )

    # =====================================
    # TOP HOLDINGS
    # =====================================

    top10 = portfolio_df.head(10)

    top5_weight = (

        portfolio_df

        .head(5)["weight_percent"]

        .sum()

    )

    top2_weight = (

        portfolio_df

        .head(2)["weight_percent"]

        .sum()

    )

    # =====================================
    # CONCENTRATION RISK
    # =====================================

    if top2_weight >= 50:

        concentration = "HIGH"

    elif top2_weight >= 35:

        concentration = "MEDIUM"

    else:

        concentration = "LOW"

    # =====================================
    # DIVERSIFICATION
    # =====================================

    sector_count = portfolio_df["sector"].nunique()

    if sector_count >= 10:

        diversification = "Excellent"

    elif sector_count >= 7:

        diversification = "Good"

    elif sector_count >= 5:

        diversification = "Average"

    else:

        diversification = "Poor"

    # =====================================
    # MARKET DATA DATE
    # =====================================
    # The trading date the current market prices are from (most holdings share the
    # same latest close date; the mode is robust to the odd stale/fallback quote).

    price_dates = portfolio_df["price_as_of"].dropna() if "price_as_of" in portfolio_df else pd.Series(dtype=object)
    market_data_date = price_dates.mode().iloc[0] if not price_dates.empty else None

    # =====================================
    # SUMMARY
    # =====================================

    summary = {

        "total_portfolio_value": total_value,

        "market_data_date": market_data_date,

        "total_holdings": len(portfolio_df),

        "total_sectors": portfolio_df["sector"].nunique(),

        "total_industries": portfolio_df["industry"].nunique(),

        "largest_sector": sector_df.iloc[0]["sector"],

        "largest_sector_weight":

            sector_df.iloc[0]["allocation_percent"],

        "largest_industry":

            industry_df.iloc[0]["industry"],

        "largest_industry_weight":

            industry_df.iloc[0]["allocation_percent"],

        "top2_weight": top2_weight,

        "top5_weight": top5_weight,

        "diversification": diversification,

        "concentration_risk": concentration

    }

    print("\n========== PORTFOLIO SUMMARY ==========\n")

    for key, value in summary.items():

        print(f"{key} : {value}")

    return {

        "portfolio": portfolio_df,

        "sector": sector_df,

        "industry": industry_df,

        "market_cap": cap_df,

        "top10": top10,

        "summary": summary

    }