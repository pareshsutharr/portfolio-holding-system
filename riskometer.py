"""Explainable, configurable Portfolio Risk-O-Meter."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy import bindparam, text
from sqlalchemy.engine import Engine

from portfolio_returns import load_all_benchmark_series


@dataclass
class RiskResult:
    name: str
    score: float
    level: str
    values: dict[str, Any]
    formula: str
    explanation: str
    coverage: str = "Complete"


def _clip(value: float) -> float:
    return round(float(np.clip(value, 0, 100)), 2)


def _risk_level(score: float, config: dict[str, Any]) -> str:
    for item in config["risk_levels"]:
        if score <= item["max"]:
            return item["label"]
    return "Very High"


def _inverse_good(value: float, good: float) -> float:
    return _clip(100 * (1 - min(max(value, 0), good) / good))


def _direct_bad(value: float, high: float) -> float:
    return _clip(100 * min(max(value, 0), high) / high)


def _log_inverse(value: float, low: float, high: float) -> float:
    if value <= low:
        return 100.0
    if value >= high:
        return 0.0
    position = (math.log(value) - math.log(low)) / (math.log(high) - math.log(low))
    return _clip(100 * (1 - position))


class Riskometer:
    def __init__(self, engine: Engine, config_path: Path) -> None:
        self.engine = engine
        self.config = json.loads(config_path.read_text(encoding="utf-8"))

    def analyze(self, holdings: pd.DataFrame) -> dict[str, Any]:
        portfolio = holdings.copy()
        portfolio["isin"] = portfolio["isin"].astype(str).str.strip().str.upper()
        portfolio["value"] = pd.to_numeric(portfolio["value"], errors="coerce")
        portfolio = portfolio.dropna(subset=["isin", "value"])
        if "ace_sector" not in portfolio:
            portfolio["ace_sector"] = pd.NA
        if "nse_sector" not in portfolio:
            portfolio["nse_sector"] = (
                portfolio["sector"] if "sector" in portfolio else pd.NA
            )
        portfolio = (
            portfolio[portfolio["value"] > 0]
            .groupby("isin", as_index=False)
            .agg(
                security_name=("security_name", "first"),
                value=("value", "sum"),
                ace_sector=("ace_sector", "first"),
                nse_sector=("nse_sector", "first"),
            )
        )
        if portfolio.empty:
            raise ValueError("The holdings file has no positive portfolio values.")
        portfolio["weight"] = portfolio["value"] / portfolio["value"].sum()
        isins = portfolio["isin"].tolist()

        with self.engine.connect() as connection:
            master = self._query(
                connection,
                """
                SELECT c.isin, c.company_name, c.sector AS master_sector
                FROM company_master c
                WHERE c.isin IN :isins
                """,
                isins,
            )
            fundamentals = self._query(
                connection,
                """
                SELECT DISTINCT ON (isin) isin, financial_year, roe, roce,
                       interest_cover, debt_equity
                FROM fundamentals WHERE isin IN :isins
                ORDER BY isin, financial_year DESC
                """,
                isins,
            )
            market = self._query(
                connection,
                """
                SELECT isin, trade_date, close_price, volume, turnover
                FROM daily_market_data WHERE isin IN :isins
                ORDER BY isin, trade_date
                """,
                isins,
            )

        cap = self._load_market_caps()
        portfolio = portfolio.merge(master, on="isin", how="left").merge(cap, on="isin", how="left")
        portfolio["ace_sector"] = portfolio["ace_sector"].fillna(
            portfolio["master_sector"]
        )
        sector_mapping_path = Path("sector_mapping.json")
        sector_mapping = (
            json.loads(sector_mapping_path.read_text(encoding="utf-8"))
            if sector_mapping_path.exists()
            else {}
        )
        mapped_sector = portfolio["ace_sector"].map(sector_mapping)
        portfolio["nse_sector"] = (
            portfolio["nse_sector"]
            .fillna(mapped_sector)
            .fillna(portfolio["ace_sector"])
            .fillna("Unmapped")
        )
        portfolio["cap_category"] = portfolio["cap_category"].fillna("Unknown")

        results = [
            self._concentration(portfolio),
            self._sector(portfolio),
            self._market_cap(portfolio),
            self._quality(portfolio, fundamentals),
            self._liquidity(portfolio, market),
            self._volatility(portfolio, market),
            self._beta(portfolio, market),
        ]
        weights = self.config["module_weights"]
        overall = sum(result.score * weights[result.name] for result in results)
        return {
            "portfolio": portfolio,
            "results": results,
            "overall_score": _clip(overall),
            "overall_level": _risk_level(overall, self.config),
            "total_value": float(portfolio["value"].sum()),
        }

    @staticmethod
    def _query(connection: Any, sql: str, isins: list[str]) -> pd.DataFrame:
        statement = text(sql).bindparams(bindparam("isins", expanding=True))
        return pd.read_sql(statement, connection, params={"isins": isins})

    @staticmethod
    def _load_market_caps() -> pd.DataFrame:
        frame = pd.read_excel("test_files/MCap.xlsx", header=1)
        frame = frame[
            ["ISIN", "Categorization as per SEBI Circular dated Oct 6, 2017"]
        ].rename(
            columns={
                "ISIN": "isin",
                "Categorization as per SEBI Circular dated Oct 6, 2017": "cap_category",
            }
        )
        frame["isin"] = frame["isin"].astype(str).str.strip().str.upper()
        return frame.drop_duplicates("isin")

    def _result(
        self, name: str, score: float, values: dict[str, Any], formula: str,
        explanation: str, coverage: str = "Complete"
    ) -> RiskResult:
        score = _clip(score)
        return RiskResult(
            name, score, _risk_level(score, self.config), values, formula,
            explanation, coverage
        )

    def _concentration(self, p: pd.DataFrame) -> RiskResult:
        weights = p["weight"].sort_values(ascending=False)
        largest, top3, top5, hhi = (
            weights.iloc[0] * 100,
            weights.head(3).sum() * 100,
            weights.head(5).sum() * 100,
            float((weights**2).sum()),
        )
        c = self.config["concentration"]
        score = np.mean([
            _direct_bad(largest, c["largest_holding_high"]),
            _direct_bad(top3, c["top3_high"]),
            _direct_bad(top5, c["top5_high"]),
            _direct_bad(hhi, c["hhi_high"]),
        ])
        return self._result(
            "concentration", score,
            {"Largest holding": f"{largest:.2f}%", "Top 3": f"{top3:.2f}%",
             "Top 5": f"{top5:.2f}%", "HHI": round(hhi, 4)},
            "Average of normalized largest-holding, top-3, top-5 and HHI risks.",
            f"The largest holding is {largest:.2f}% and the top five represent {top5:.2f}%.",
        )

    def _sector(self, p: pd.DataFrame) -> RiskResult:
        allocations = p.groupby("nse_sector")["weight"].sum()
        largest = float(allocations.max() * 100)
        hhi = float((allocations**2).sum())
        count = int(len(allocations))
        c = self.config["sector"]
        score = np.mean([
            _direct_bad(largest, c["largest_sector_high"]),
            _direct_bad(hhi, c["sector_hhi_high"]),
            _inverse_good(count, c["well_diversified_sector_count"]),
        ])
        return self._result(
            "sector", score,
            {"Largest sector": f"{allocations.idxmax()} ({largest:.2f}%)",
             "Sector count": count, "Sector HHI": round(hhi, 4)},
            "Average of normalized largest-sector, sector-HHI and sector-count risks.",
            f"The portfolio spans {count} NSE sectors; the largest is {allocations.idxmax()}.",
        )

    def _market_cap(self, p: pd.DataFrame) -> RiskResult:
        allocation = p.groupby("cap_category")["weight"].sum()
        scores = self.config["market_cap_scores"]
        score = sum(weight * scores.get(category, scores["Unknown"]) for category, weight in allocation.items())
        values = {str(category): f"{weight * 100:.2f}%" for category, weight in allocation.items()}
        return self._result(
            "market_cap", score, values,
            "Portfolio-weighted configured risk score for each SEBI market-cap category.",
            "Higher Small Cap, Micro Cap or unknown exposure increases market-cap risk.",
        )

    def _quality(self, p: pd.DataFrame, f: pd.DataFrame) -> RiskResult:
        classifications = p[
            ["isin", "security_name", "weight", "ace_sector", "nse_sector"]
        ].copy()
        labels = (
            classifications[
                ["security_name", "ace_sector", "nse_sector"]
            ]
            .fillna("")
            .astype(str)
            .agg(" ".join, axis=1)
            .str.upper()
        )
        classifications["is_etf"] = labels.str.contains(
            r"\bETF\b|EXCHANGE TRADED|GOLD\s*BEES|NETF(?:GOLD|SILVER)",
            regex=True,
        )
        classifications["is_financial"] = labels.str.contains(
            r"\bBANK\b|FINANCIAL SERVICES|\bFINANCE\b|NBFC|INSURANCE",
            regex=True,
        )

        eligible = classifications[~classifications["is_etf"]].copy()
        merged = eligible.merge(f, on="isin", how="left")
        c = self.config["quality"]

        def stock_quality_score(row: pd.Series) -> float:
            required = ["roe", "roce", "debt_equity"]
            if not row["is_financial"]:
                required.append("interest_cover")
            if any(pd.isna(row[column]) for column in required):
                return np.nan

            component_scores = [
                _inverse_good(float(row["roe"]), c["roe_good"]),
                _inverse_good(float(row["roce"]), c["roce_good"]),
                _direct_bad(float(row["debt_equity"]), c["debt_equity_high"]),
            ]
            # Interest coverage is not meaningful for banks and financial institutions.
            if not row["is_financial"]:
                component_scores.append(
                    _inverse_good(float(row["interest_cover"]), c["interest_cover_good"])
                )
            return float(np.mean(component_scores))

        merged["stock_score"] = merged.apply(stock_quality_score, axis=1)
        calculable = merged.dropna(subset=["stock_score"]).copy()
        if calculable.empty:
            return self._result(
                "quality", 100, {},
                "No calculable eligible company records.",
                "No usable company fundamentals were available; ETFs were not scored.",
                "0% of eligible company value",
            )

        eligible_weight = float(eligible["weight"].sum())
        covered_weight = float(calculable["weight"].sum())
        covered = covered_weight / eligible_weight if eligible_weight else 0.0
        score = float(
            np.average(calculable["stock_score"], weights=calculable["weight"])
        )

        def weighted_metric(column: str, *, exclude_financials: bool = False) -> str:
            available = calculable
            if exclude_financials:
                available = available[~available["is_financial"]]
            available = available.dropna(subset=[column])
            if available.empty:
                return "N/A"
            return f"{np.average(available[column], weights=available['weight']):.2f}"

        excluded_etfs = classifications[classifications["is_etf"]]
        financials = calculable[calculable["is_financial"]]
        values = {
            "Weighted ROE": f"{weighted_metric('roe')}%",
            "Weighted ROCE": f"{weighted_metric('roce')}%",
            "Weighted Debt/Equity": weighted_metric("debt_equity"),
            "Weighted Interest Cover": (
                f"{weighted_metric('interest_cover', exclude_financials=True)}x"
            ),
            "ETFs excluded": int(len(excluded_etfs)),
            "Financials with Interest Cover N/A": int(len(financials)),
        }
        return self._result(
            "quality", score, values,
            "Eligible-company score = average of applicable ROE, ROCE, Debt/Equity "
            "and Interest Cover risks; scores are portfolio weighted.",
            "ETFs are excluded from company-quality scoring. Interest Cover is "
            "Not Applicable for banks and financial institutions.",
            f"{covered * 100:.1f}% of eligible company value",
        )

    def _liquidity(self, p: pd.DataFrame, market: pd.DataFrame) -> RiskResult:
        days = self.config["history"]["liquidity_days"]
        recent = market.sort_values("trade_date").groupby("isin").tail(days)
        metrics = recent.groupby("isin").agg(volume=("volume", "mean"), turnover=("turnover", "mean")).reset_index()
        merged = p[["isin", "weight", "cap_category"]].merge(metrics, on="isin").dropna()
        if merged.empty:
            return self._result("liquidity", 100, {}, "No calculable records.",
                                "No liquidity history was available.", "0%")

        tiers = self.config["liquidity"]
        fallback_tier = tiers[self.config["liquidity_fallback_tier"]]

        def stock_liquidity_score(row: pd.Series) -> float:
            tier = tiers.get(row["cap_category"], fallback_tier)
            volume_risk = _log_inverse(float(row["volume"]), tier["volume_low_thousand"], tier["volume_high_thousand"])
            turnover_risk = _log_inverse(float(row["turnover"]), tier["turnover_low_crore"], tier["turnover_high_crore"])
            return (volume_risk + turnover_risk) / 2

        merged["stock_score"] = merged.apply(stock_liquidity_score, axis=1)
        covered = float(merged["weight"].sum())
        score = float(np.average(merged["stock_score"], weights=merged["weight"]))
        return self._result(
            "liquidity", score,
            {"Weighted average volume ('000)": round(float(np.average(merged["volume"], weights=merged["weight"])), 2),
             "Weighted average turnover (Cr)": round(float(np.average(merged["turnover"], weights=merged["weight"])), 2)},
            "Average log-normalized 63-day volume and turnover risk against the stock's own "
            "market-cap-tier threshold, portfolio weighted.",
            "Higher average traded volume and turnover reduce exit-liquidity risk. Each stock is "
            "judged against its own cap-tier band, not one universal band.",
            f"{covered * 100:.1f}% of portfolio value",
        )

    def _return_metrics(self, market: pd.DataFrame) -> pd.DataFrame:
        days = self.config["history"]["trading_days"]
        rows = []
        for isin, group in market.groupby("isin"):
            prices = group.dropna(subset=["close_price"]).sort_values("trade_date").tail(days)
            returns = prices.set_index("trade_date")["close_price"].astype(float).pct_change().dropna()
            if len(returns) < self.config["history"]["minimum_return_observations"]:
                continue
            wealth = (1 + returns).cumprod()
            drawdown = wealth / wealth.cummax() - 1
            downside = returns[returns < 0]
            rows.append({
                "isin": isin, "volatility": returns.std() * np.sqrt(252),
                "drawdown": abs(drawdown.min()),
                "downside": downside.std() * np.sqrt(252) if len(downside) > 1 else 0,
                "returns": returns,
            })
        return pd.DataFrame(rows)

    def _volatility(self, p: pd.DataFrame, market: pd.DataFrame) -> RiskResult:
        metrics = self._return_metrics(market)
        if metrics.empty:
            return self._result("volatility", 100, {}, "No calculable records.",
                                "Insufficient price history.", "0%")
        merged = p[["isin", "weight"]].merge(metrics.drop(columns=["returns"]), on="isin")
        if merged.empty:
            return self._result("volatility", 100, {}, "No calculable records.",
                                "Insufficient price history.", "0%")
        c = self.config["volatility"]
        merged["stock_score"] = (
            merged["volatility"].map(lambda x: _direct_bad(x, c["annualized_volatility_high"]))
            + merged["drawdown"].map(lambda x: _direct_bad(x, c["maximum_drawdown_high"]))
            + merged["downside"].map(lambda x: _direct_bad(x, c["downside_volatility_high"]))
        ) / 3
        covered = float(merged["weight"].sum())
        score = float(np.average(merged["stock_score"], weights=merged["weight"]))
        return self._result(
            "volatility", score,
            {"Annualized volatility": f"{np.average(merged['volatility'], weights=merged['weight']) * 100:.2f}%",
             "Maximum drawdown": f"{np.average(merged['drawdown'], weights=merged['weight']) * 100:.2f}%",
             "Downside volatility": f"{np.average(merged['downside'], weights=merged['weight']) * 100:.2f}%"},
            "Average normalized annual volatility, maximum drawdown and downside-volatility risks, portfolio weighted.",
            "Larger price fluctuations and drawdowns increase volatility risk.",
            f"{covered * 100:.1f}% of portfolio value",
        )

    def _beta(self, p: pd.DataFrame, market: pd.DataFrame) -> RiskResult:
        metrics = self._return_metrics(market)
        if metrics.empty:
            return self._result("beta", 100, {}, "No calculable records.",
                                "Stock-return history was unavailable.", "0%")

        beta_cfg = self.config["beta"]
        benchmark_by_cap = beta_cfg["benchmark_by_cap"]
        fallback_benchmark = beta_cfg["benchmark_fallback"]
        cap_by_isin = p.set_index("isin")["cap_category"]

        benchmark_prices = load_all_benchmark_series()
        benchmark_returns = {
            name: series.pct_change().dropna()
            for name, series in benchmark_prices.items()
        }

        rows = []
        for row in metrics.itertuples():
            cap_category = cap_by_isin.get(row.isin, "Unknown")
            benchmark_name = benchmark_by_cap.get(cap_category, fallback_benchmark)
            returns = benchmark_returns[benchmark_name]
            aligned = pd.concat([row.returns.rename("stock"), returns.rename("benchmark")], axis=1).dropna()
            if len(aligned) < self.config["history"]["minimum_return_observations"] or aligned["benchmark"].var() == 0:
                continue
            beta = aligned["stock"].cov(aligned["benchmark"]) / aligned["benchmark"].var()
            rows.append({"isin": row.isin, "beta": beta})
        merged = p[["isin", "weight"]].merge(pd.DataFrame(rows), on="isin")
        if merged.empty:
            return self._result("beta", 100, {}, "No calculable records.",
                                "Insufficient overlapping benchmark dates.", "0%")
        low, high = beta_cfg["low"], beta_cfg["high"]
        merged["stock_score"] = merged["beta"].map(lambda x: _clip((float(x) - low) / (high - low) * 100))
        covered = float(merged["weight"].sum())
        beta = float(np.average(merged["beta"], weights=merged["weight"]))
        score = float(np.average(merged["stock_score"], weights=merged["weight"]))
        return self._result(
            "beta", score, {"Portfolio-weighted beta": round(beta, 3)},
            "Stock beta = covariance(stock, cap-appropriate benchmark) / variance(cap-appropriate "
            "benchmark); Large Cap uses Nifty 50, Mid Cap uses Nifty Midcap 150, Small Cap uses "
            "Nifty 500; stock risks are portfolio weighted.",
            f"A weighted beta of {beta:.2f} indicates {'aggressive' if beta > 1 else 'defensive'} market sensitivity.",
            f"{covered * 100:.1f}% of portfolio value",
        )
