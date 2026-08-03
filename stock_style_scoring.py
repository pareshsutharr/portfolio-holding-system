"""Generic percentile-based scoring engine driven by style_config.json.

For every metric defined in the config:
  - a 0-100 score is computed as the metric's percentile rank across the
    full Accord market universe (direction-aware: for "lower_better"
    metrics, a lower raw value earns a higher score).
  - eligibility is a separate pass/fail check against the metric's stated
    minimum requirement (a fixed threshold, or the universe median/mean).

A style's Style Score is the weighted average of its available metric
scores (weights renormalized over whichever metrics have data). A style is
"eligible" only if the stock clears the style's "pass at least N of M"
rule; ineligible styles still get a score for transparency but can never
become a stock's Primary or Secondary Style.
"""

import operator

import numpy as np
import pandas as pd

COMPARATORS = {
    ">=": operator.ge,
    "<=": operator.le,
    ">": operator.gt,
    "<": operator.lt,
    "==": operator.eq,
}


def _percentile_score(series, direction):
    if direction == "boolean":
        return series.astype("Float64").astype(float) * 100.0
    rank_pct = series.rank(pct=True, method="average")
    if direction == "lower_better":
        rank_pct = 1 - rank_pct
    return rank_pct * 100.0


def _threshold_value(series, metric):
    threshold_type = metric["threshold_type"]
    if threshold_type == "fixed":
        return metric["threshold"]
    if threshold_type == "median":
        return series.median(skipna=True)
    if threshold_type == "mean":
        return series.mean(skipna=True)
    raise ValueError(f"Unknown threshold_type: {threshold_type}")


def _eligibility(series, metric):
    threshold = _threshold_value(series, metric)
    compare = COMPARATORS[metric["compare"]]
    raw = series.astype(float) if series.dtype != object else pd.to_numeric(series, errors="coerce")
    passed = raw.apply(lambda v: bool(compare(v, threshold)) if pd.notna(v) else False)
    return passed, threshold


def score_universe(universe_df, config):
    """Adds `<key>_score`, `<key>_pass` columns per metric and
    `<style>_score`, `<style>_eligible`, `<style>_pass_count`,
    `<style>_available_count`, `<style>_total_metrics` per style.

    `available_count` vs `total_metrics` lets the report distinguish a stock
    that is ineligible because it genuinely underperforms on the metrics it
    HAS data for, from one that is ineligible only because too few metrics
    could even be computed (e.g. a recently listed IPO that doesn't yet have
    5 years of history for Growth) -- see
    Stock_Style_Rating_and_Scoring_Methodology_v1.docx."""

    df = universe_df.copy()
    style_score_columns = []
    metric_meta = {}

    for style_key, style_cfg in config["styles"].items():
        metric_keys = [m["key"] for m in style_cfg["metrics"]]
        weighted_sum = pd.Series(0.0, index=df.index)
        weight_total = pd.Series(0.0, index=df.index)
        pass_count = pd.Series(0, index=df.index)
        available_count = pd.Series(0, index=df.index)

        for metric in style_cfg["metrics"]:
            key = metric["key"]
            if key not in df.columns:
                df[key] = np.nan

            score = _percentile_score(df[key], metric["direction"])
            passed, threshold = _eligibility(df[key], metric)

            df[f"{key}_score"] = score
            df[f"{key}_pass"] = passed
            metric_meta[key] = {**metric, "style": style_key, "threshold_value": threshold}

            available = score.notna()
            weighted_sum = weighted_sum.add(score.fillna(0) * metric["weight"] * available, fill_value=0)
            weight_total = weight_total.add(metric["weight"] * available, fill_value=0)
            pass_count = pass_count.add(passed.astype(int), fill_value=0)
            available_count = available_count.add(available.astype(int), fill_value=0)

        style_score = (weighted_sum / weight_total.replace(0, np.nan))
        df[f"{style_key}_score"] = style_score
        df[f"{style_key}_pass_count"] = pass_count
        df[f"{style_key}_available_count"] = available_count
        df[f"{style_key}_total_metrics"] = len(metric_keys)
        df[f"{style_key}_eligible"] = pass_count >= style_cfg["min_pass"]
        style_score_columns.append(style_key)

    df.attrs["metric_meta"] = metric_meta
    df.attrs["style_keys"] = style_score_columns
    return df


def classify_primary_secondary(df, config):
    style_keys = df.attrs["style_keys"]

    def _rank_row(row):
        eligible = [
            (key, row[f"{key}_score"])
            for key in style_keys
            if row[f"{key}_eligible"] and pd.notna(row[f"{key}_score"])
        ]
        eligible.sort(key=lambda pair: pair[1], reverse=True)
        primary = eligible[0] if len(eligible) >= 1 else (None, np.nan)
        secondary = eligible[1] if len(eligible) >= 2 else (None, np.nan)
        return pd.Series({
            "primary_style": primary[0],
            "primary_score": primary[1],
            "secondary_style": secondary[0],
            "secondary_score": secondary[1],
        })

    classification = df.apply(_rank_row, axis=1)
    result = pd.concat([df, classification], axis=1)
    result["rating"] = result["primary_score"].apply(lambda s: rating_for_score(s, config))
    result.attrs = df.attrs
    return result


def rating_for_score(score, config):
    if pd.isna(score):
        return "Unclassified"
    for band in config["rating_bands"]:
        if score >= band["min"]:
            return band["rating"]
    return config["rating_bands"][-1]["rating"]
