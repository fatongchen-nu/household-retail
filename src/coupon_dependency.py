from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from rfm_segmentation import compute_household_rfm


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
TABLEAU_DIR = PROJECT_ROOT / "tableau"


def _safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0 or pd.isna(denominator):
        return 0.0
    return float(numerator / denominator)


def _recommend(row: pd.Series) -> str:
    if row["coupon_redemptions"] == 0:
        if row["segment"] in {"Hibernating", "At Risk High Value"}:
            return "Winback Test"
        return "No Deal Needed"

    if row["available_post_days"] < 30:
        return "Insufficient Post Window"

    if row["post_90d_baskets"] == 0:
        return "Stop Subsidy"

    if row["full_price_post_90d_sales"] > 0 and row["post_90d_sales"] >= row["pre_90d_sales"]:
        if row["coupon_dependency_ratio"] <= 0.5:
            return "Keep Deal"
        return "Reduce Deal"

    if row["deal_only_after_coupon_flag"] or row["deal_dependency_ratio"] >= 0.8:
        return "Reduce Deal"

    if row["post_90d_sales"] < row["pre_90d_sales"] * 0.5:
        return "Stop Subsidy"

    return "Test Smaller Deal"


def compute_household_coupon_scores(
    transaction_path: Path = DATA_DIR / "transaction_data.csv",
    redemption_path: Path = DATA_DIR / "coupon_redempt.csv",
) -> pd.DataFrame:
    transactions = pd.read_csv(
        transaction_path,
        usecols=[
            "household_key",
            "BASKET_ID",
            "DAY",
            "SALES_VALUE",
            "RETAIL_DISC",
            "COUPON_DISC",
            "COUPON_MATCH_DISC",
        ],
    )
    redemptions = pd.read_csv(redemption_path)
    max_day = int(transactions["DAY"].max())

    transactions["coupon_discount_abs"] = (
        transactions["COUPON_DISC"].abs() + transactions["COUPON_MATCH_DISC"].abs()
    )
    transactions["deal_discount_abs"] = (
        transactions["RETAIL_DISC"].clip(upper=0).abs()
        + transactions["COUPON_DISC"].clip(upper=0).abs()
        + transactions["COUPON_MATCH_DISC"].clip(upper=0).abs()
    )
    transactions["is_coupon_line"] = transactions["coupon_discount_abs"] > 0
    transactions["is_deal_line"] = transactions["deal_discount_abs"] > 0
    transactions["is_full_price_line"] = transactions["deal_discount_abs"] == 0

    base = (
        transactions.groupby("household_key")
        .agg(
            total_sales=("SALES_VALUE", "sum"),
            total_baskets=("BASKET_ID", "nunique"),
            total_purchase_days=("DAY", "nunique"),
            first_purchase_day=("DAY", "min"),
            last_purchase_day=("DAY", "max"),
            coupon_discount_abs=("coupon_discount_abs", "sum"),
            deal_discount_abs=("deal_discount_abs", "sum"),
        )
        .reset_index()
    )
    coupon_sales = (
        transactions.loc[transactions["is_coupon_line"]]
        .groupby("household_key")["SALES_VALUE"]
        .sum()
        .rename("coupon_sales")
    )
    deal_sales = (
        transactions.loc[transactions["is_deal_line"]]
        .groupby("household_key")["SALES_VALUE"]
        .sum()
        .rename("deal_sales")
    )
    coupon_baskets = (
        transactions.loc[transactions["is_coupon_line"]]
        .groupby("household_key")["BASKET_ID"]
        .nunique()
        .rename("coupon_baskets")
    )
    deal_baskets = (
        transactions.loc[transactions["is_deal_line"]]
        .groupby("household_key")["BASKET_ID"]
        .nunique()
        .rename("deal_baskets")
    )
    first_redemption = (
        redemptions.groupby("household_key")
        .agg(
            first_coupon_day=("DAY", "min"),
            last_coupon_day=("DAY", "max"),
            coupon_redemptions=("COUPON_UPC", "count"),
            redeemed_campaigns=("CAMPAIGN", "nunique"),
        )
        .reset_index()
    )

    household = (
        base.merge(coupon_sales, on="household_key", how="left")
        .merge(deal_sales, on="household_key", how="left")
        .merge(coupon_baskets, on="household_key", how="left")
        .merge(deal_baskets, on="household_key", how="left")
        .merge(first_redemption, on="household_key", how="left")
    )
    fill_cols = [
        "coupon_sales",
        "deal_sales",
        "coupon_baskets",
        "deal_baskets",
        "coupon_redemptions",
        "redeemed_campaigns",
    ]
    household[fill_cols] = household[fill_cols].fillna(0)
    household["coupon_user_flag"] = household["coupon_redemptions"] > 0
    household["coupon_dependency_ratio"] = household.apply(
        lambda row: _safe_divide(row["coupon_sales"], row["total_sales"]), axis=1
    )
    household["deal_dependency_ratio"] = household.apply(
        lambda row: _safe_divide(row["deal_sales"], row["total_sales"]), axis=1
    )

    coupon_users = household.loc[household["coupon_user_flag"], ["household_key", "first_coupon_day"]]
    txn_with_coupon_day = transactions.merge(coupon_users, on="household_key", how="inner")

    def window_sales(days_after_start: int, days_after_end: int | None = None) -> pd.Series:
        if days_after_end is None:
            mask = txn_with_coupon_day["DAY"].between(
                txn_with_coupon_day["first_coupon_day"] + days_after_start,
                max_day,
            )
        else:
            mask = txn_with_coupon_day["DAY"].between(
                txn_with_coupon_day["first_coupon_day"] + days_after_start,
                txn_with_coupon_day["first_coupon_day"] + days_after_end,
            )
        return txn_with_coupon_day.loc[mask].groupby("household_key")["SALES_VALUE"].sum()

    def window_baskets(days_after_start: int, days_after_end: int | None = None) -> pd.Series:
        if days_after_end is None:
            mask = txn_with_coupon_day["DAY"].between(
                txn_with_coupon_day["first_coupon_day"] + days_after_start,
                max_day,
            )
        else:
            mask = txn_with_coupon_day["DAY"].between(
                txn_with_coupon_day["first_coupon_day"] + days_after_start,
                txn_with_coupon_day["first_coupon_day"] + days_after_end,
            )
        return txn_with_coupon_day.loc[mask].groupby("household_key")["BASKET_ID"].nunique()

    pre_90_mask = txn_with_coupon_day["DAY"].between(
        txn_with_coupon_day["first_coupon_day"] - 90,
        txn_with_coupon_day["first_coupon_day"] - 1,
    )
    post_90_mask = txn_with_coupon_day["DAY"].between(
        txn_with_coupon_day["first_coupon_day"] + 1,
        txn_with_coupon_day["first_coupon_day"] + 90,
    )
    full_price_post_90 = (
        txn_with_coupon_day.loc[post_90_mask & txn_with_coupon_day["is_full_price_line"]]
        .groupby("household_key")["SALES_VALUE"]
        .sum()
    )
    deal_post_90 = (
        txn_with_coupon_day.loc[post_90_mask & txn_with_coupon_day["is_deal_line"]]
        .groupby("household_key")["SALES_VALUE"]
        .sum()
    )

    window_metrics = pd.DataFrame({"household_key": household["household_key"]})
    window_metrics = window_metrics.merge(
        txn_with_coupon_day.loc[pre_90_mask].groupby("household_key")["SALES_VALUE"].sum().rename("pre_90d_sales"),
        on="household_key",
        how="left",
    )
    for days in (30, 60, 90):
        window_metrics = window_metrics.merge(
            window_sales(1, days).rename(f"post_{days}d_sales"),
            on="household_key",
            how="left",
        ).merge(
            window_baskets(1, days).rename(f"post_{days}d_baskets"),
            on="household_key",
            how="left",
        )
    window_metrics = window_metrics.merge(
        full_price_post_90.rename("full_price_post_90d_sales"),
        on="household_key",
        how="left",
    ).merge(
        deal_post_90.rename("deal_post_90d_sales"),
        on="household_key",
        how="left",
    )

    household = household.merge(window_metrics, on="household_key", how="left")
    metric_cols = [
        "pre_90d_sales",
        "post_30d_sales",
        "post_30d_baskets",
        "post_60d_sales",
        "post_60d_baskets",
        "post_90d_sales",
        "post_90d_baskets",
        "full_price_post_90d_sales",
        "deal_post_90d_sales",
    ]
    household[metric_cols] = household[metric_cols].fillna(0)
    household["available_post_days"] = np.where(
        household["coupon_user_flag"],
        max_day - household["first_coupon_day"],
        0,
    )
    household["post_coupon_repeat_flag"] = household["post_90d_baskets"] > 0
    household["full_price_after_coupon_flag"] = household["full_price_post_90d_sales"] > 0
    household["deal_only_after_coupon_flag"] = (
        household["post_coupon_repeat_flag"]
        & ~household["full_price_after_coupon_flag"]
        & (household["deal_post_90d_sales"] > 0)
    )
    household["post_90d_incremental_vs_pre_90d"] = household["post_90d_sales"] - household["pre_90d_sales"]
    household["subsidy_efficiency"] = household.apply(
        lambda row: _safe_divide(row["post_90d_incremental_vs_pre_90d"], row["coupon_discount_abs"]),
        axis=1,
    )

    rfm = compute_household_rfm()[
        [
            "household_key",
            "segment",
            "recency_days",
            "frequency_baskets",
            "monetary_sales",
            "avg_basket_value",
        ]
    ]
    household = household.merge(rfm, on="household_key", how="left")
    household["deal_strategy_recommendation"] = household.apply(_recommend, axis=1)

    numeric_cols = household.select_dtypes(include=["number"]).columns
    household[numeric_cols] = household[numeric_cols].round(6)
    return household.sort_values(
        ["coupon_user_flag", "post_90d_incremental_vs_pre_90d", "total_sales"],
        ascending=[False, False, False],
    )


def summarize_coupon_dependency(household_scores: pd.DataFrame) -> pd.DataFrame:
    coupon_users = household_scores[household_scores["coupon_user_flag"]]
    total_coupon_users = coupon_users["household_key"].nunique()

    summary = (
        household_scores.groupby("segment")
        .agg(
            households=("household_key", "nunique"),
            coupon_households=("coupon_user_flag", "sum"),
            avg_total_sales=("total_sales", "mean"),
            avg_coupon_dependency_ratio=("coupon_dependency_ratio", "mean"),
            avg_deal_dependency_ratio=("deal_dependency_ratio", "mean"),
            avg_coupon_discount_abs=("coupon_discount_abs", "mean"),
            avg_pre_90d_sales=("pre_90d_sales", "mean"),
            avg_post_30d_sales=("post_30d_sales", "mean"),
            avg_post_60d_sales=("post_60d_sales", "mean"),
            avg_post_90d_sales=("post_90d_sales", "mean"),
            post_30d_repeat_households=("post_30d_baskets", lambda values: int((values > 0).sum())),
            post_60d_repeat_households=("post_60d_baskets", lambda values: int((values > 0).sum())),
            post_90d_repeat_households=("post_90d_baskets", lambda values: int((values > 0).sum())),
            full_price_post_90d_households=("full_price_after_coupon_flag", "sum"),
            deal_only_after_coupon_households=("deal_only_after_coupon_flag", "sum"),
            avg_post_90d_incremental_vs_pre_90d=("post_90d_incremental_vs_pre_90d", "mean"),
            total_post_90d_incremental_vs_pre_90d=("post_90d_incremental_vs_pre_90d", "sum"),
            avg_subsidy_efficiency=("subsidy_efficiency", "mean"),
        )
        .reset_index()
    )
    summary["coupon_user_rate"] = summary.apply(
        lambda row: _safe_divide(row["coupon_households"], row["households"]), axis=1
    )
    for days in (30, 60, 90):
        summary[f"post_{days}d_repeat_rate_among_coupon_users"] = summary.apply(
            lambda row, d=days: _safe_divide(row[f"post_{d}d_repeat_households"], row["coupon_households"]),
            axis=1,
        )
    summary["full_price_post_90d_rate_among_coupon_users"] = summary.apply(
        lambda row: _safe_divide(row["full_price_post_90d_households"], row["coupon_households"]),
        axis=1,
    )
    summary["deal_only_after_coupon_rate"] = summary.apply(
        lambda row: _safe_divide(row["deal_only_after_coupon_households"], row["coupon_households"]),
        axis=1,
    )
    summary["coupon_user_share"] = summary["coupon_households"] / total_coupon_users if total_coupon_users else 0

    recommendations = (
        household_scores.groupby(["segment", "deal_strategy_recommendation"])["household_key"]
        .nunique()
        .unstack(fill_value=0)
        .reset_index()
    )
    summary = summary.merge(recommendations, on="segment", how="left")
    recommendation_cols = [
        "Keep Deal",
        "Reduce Deal",
        "Stop Subsidy",
        "Test Smaller Deal",
        "Winback Test",
        "No Deal Needed",
        "Insufficient Post Window",
    ]
    for col in recommendation_cols:
        if col not in summary:
            summary[col] = 0

    def segment_recommendation(row: pd.Series) -> str:
        if row["Winback Test"] >= row["households"] * 0.35:
            return "Run controlled winback test"
        if row["coupon_households"] == 0:
            return "No coupon readout yet"
        if row["Stop Subsidy"] >= row["coupon_households"] * 0.35 and row["coupon_households"] > 0:
            return "Reduce or stop broad couponing"
        if row["Keep Deal"] >= row["coupon_households"] * 0.35:
            return "Continue targeted deals"
        if row["Reduce Deal"] + row["Test Smaller Deal"] >= row["coupon_households"] * 0.35:
            return "Use smaller or less frequent deals"
        return "Maintain selective testing"

    summary["segment_coupon_strategy"] = summary.apply(segment_recommendation, axis=1)
    numeric_cols = summary.select_dtypes(include=["number"]).columns
    summary[numeric_cols] = summary[numeric_cols].round(6)
    return summary.sort_values(
        ["total_post_90d_incremental_vs_pre_90d", "coupon_households"], ascending=False
    )


def run(
    segment_output_path: Path = TABLEAU_DIR / "coupon_dependency.csv",
    household_output_path: Path = TABLEAU_DIR / "coupon_household_scores.csv",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    TABLEAU_DIR.mkdir(parents=True, exist_ok=True)
    household_scores = compute_household_coupon_scores()
    segment_summary = summarize_coupon_dependency(household_scores)
    household_scores.to_csv(household_output_path, index=False)
    segment_summary.to_csv(segment_output_path, index=False)
    return household_scores, segment_summary


if __name__ == "__main__":
    households, segments = run()
    print(
        f"Wrote {len(segments)} segment rows to {TABLEAU_DIR / 'coupon_dependency.csv'} "
        f"and {len(households)} household rows to {TABLEAU_DIR / 'coupon_household_scores.csv'}"
    )
