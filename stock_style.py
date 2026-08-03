"""Stock Style Classification: classifies every portfolio holding into
Growth / Value / Momentum / Quality / Low Volatility / Liquidity style
scores (plus a Size classification), following
Stock_Style_Rating_and_Scoring_Methodology_v1.docx.

Percentile scores and eligibility are computed against the full Accord
market universe (~7,000 companies), not just the portfolio holdings, so
"top decile" / "market median" comparisons are meaningful.
"""

import json

import numpy as np
import pandas as pd

from market_cap import load_market_cap_master
from stock_style_market import compute_momentum_low_vol_universe
from stock_style_scoring import classify_primary_secondary, score_universe
from stock_style_universe import (
    load_growth_universe,
    load_liquidity_universe,
    load_quality_universe,
    load_value_universe,
)


class StockStyleClassifier:
    def __init__(self, config_path):
        self.config = json.loads(config_path.read_text(encoding="utf-8"))

    def _build_universe(self):
        growth = load_growth_universe()
        value = load_value_universe()
        quality = load_quality_universe()
        liquidity = load_liquidity_universe()
        market = compute_momentum_low_vol_universe(self.config)
        as_of_date = market.attrs.get("as_of_date") if not market.empty else None

        universe = growth.drop(columns=["company_name"]).join(
            value.drop(columns=["company_name"]), how="outer"
        ).join(
            quality.drop(columns=["company_name"]), how="outer"
        ).join(
            liquidity.drop(columns=["company_name"]), how="outer"
        ).join(
            market, how="outer"
        )

        names = growth["company_name"].combine_first(value["company_name"])
        names = names.combine_first(quality["company_name"])
        names = names.combine_first(liquidity["company_name"])
        universe["company_name"] = names

        return universe, as_of_date

    def _size_classification(self):
        cap_master = load_market_cap_master()
        cap_master = cap_master.set_index("isin")["cap_category"]
        size_cfg = self.config["size"]
        label_map = {
            size_cfg["large_cap_label"]: "Large Cap",
            size_cfg["mid_cap_label"]: "Mid Cap",
            size_cfg["small_cap_label"]: "Small Cap",
        }
        return cap_master.map(lambda v: label_map.get(v, v))

    def analyze(self, holdings):
        portfolio = holdings.copy()
        portfolio["isin"] = portfolio["isin"].astype(str).str.strip().str.upper()
        portfolio["value"] = pd.to_numeric(portfolio["value"], errors="coerce")
        portfolio = portfolio.dropna(subset=["isin", "value"])
        portfolio = (
            portfolio[portfolio["value"] > 0]
            .groupby("isin", as_index=False)
            .agg(security_name=("security_name", "first"), value=("value", "sum"))
        )
        if portfolio.empty:
            raise ValueError("The holdings file has no positive portfolio values.")
        portfolio["weight"] = portfolio["value"] / portfolio["value"].sum()

        universe, as_of_date = self._build_universe()
        scored_universe = score_universe(universe, self.config)
        classified_universe = classify_primary_secondary(scored_universe, self.config)

        size = self._size_classification()

        holdings_result = portfolio.set_index("isin").join(classified_universe, how="left")
        holdings_result["market_cap_size"] = size.reindex(holdings_result.index).fillna("Unknown")
        holdings_result["company_name"] = holdings_result["company_name"].fillna(
            holdings_result["security_name"]
        )
        holdings_result["primary_style"] = holdings_result["primary_style"].fillna("Unclassified")
        holdings_result["rating"] = holdings_result["rating"].fillna("Unclassified")
        holdings_result = holdings_result.reset_index().sort_values("weight", ascending=False)

        style_mix = (
            holdings_result.groupby("primary_style")
            .agg(
                allocation_percent=("weight", lambda w: round(float(w.sum()) * 100, 2)),
                holdings_count=("isin", "count"),
            )
            .reset_index()
            .sort_values("allocation_percent", ascending=False)
        )

        size_mix = (
            holdings_result.groupby("market_cap_size")["weight"]
            .sum()
            .mul(100)
            .round(2)
            .reset_index()
            .rename(columns={"weight": "allocation_percent"})
            .sort_values("allocation_percent", ascending=False)
        )

        coverage = float(
            (holdings_result["primary_style"] != "Unclassified").astype(int).mul(
                holdings_result["weight"]
            ).sum()
        )

        style_keys = scored_universe.attrs["style_keys"]
        profile_rows = []
        for key in style_keys:
            available = holdings_result.dropna(subset=[f"{key}_score"])
            weight_covered = float(available["weight"].sum())
            weighted_score = (
                float((available[f"{key}_score"] * available["weight"]).sum() / weight_covered)
                if weight_covered > 0 else float("nan")
            )
            profile_rows.append({
                "style": key,
                "label": self.config["styles"][key]["label"],
                "weighted_score": weighted_score,
                "coverage_percent": round(weight_covered * 100, 2),
            })
        portfolio_style_profile = pd.DataFrame(profile_rows)

        return {
            "holdings": holdings_result,
            "style_mix": style_mix,
            "size_mix": size_mix,
            "portfolio_style_profile": portfolio_style_profile,
            "style_keys": style_keys,
            "metric_meta": scored_universe.attrs["metric_meta"],
            "config": self.config,
            "as_of_date": as_of_date,
            "coverage": coverage,
            "total_value": float(portfolio["value"].sum()),
        }
