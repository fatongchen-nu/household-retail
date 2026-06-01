from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
TABLEAU_DIR = PROJECT_ROOT / "tableau"


DEMO_COLUMNS = [
    "classification_1",
    "classification_2",
    "classification_3",
    "classification_4",
    "classification_5",
    "HOMEOWNER_DESC",
    "KID_CATEGORY_DESC",
]


def _score_quantiles(series: pd.Series, higher_is_better: bool = True) -> pd.Series:
    """Return a 1-5 score using ranks so qcut works even with many ties."""
    ascending_rank = higher_is_better
    ranks = series.rank(method="first", ascending=ascending_rank)
    return pd.qcut(ranks, q=5, labels=[1, 2, 3, 4, 5]).astype(int)


def _assign_segment(row: pd.Series) -> str:
    r, f, m = int(row["r_score"]), int(row["f_score"]), int(row["m_score"])
    if r >= 4 and f >= 4 and m >= 4:
        return "Champions"
    if r >= 3 and f >= 4:
        return "Loyal Customers"
    if r >= 4 and f in (2, 3):
        return "Potential Loyalists"
    if r == 5 and f <= 2:
        return "New or Recent"
    if m == 5 and f <= 3:
        return "Big Spenders"
    if r <= 2 and (f >= 4 or m >= 4):
        return "At Risk High Value"
    if r <= 2 and f <= 2:
        return "Hibernating"
    return "Needs Attention"


def compute_household_rfm(
    transaction_path: Path = DATA_DIR / "transaction_data.csv",
    demographic_path: Path = DATA_DIR / "hh_demographic.csv",
) -> pd.DataFrame:
    transactions = pd.read_csv(
        transaction_path,
        usecols=[
            "household_key",
            "BASKET_ID",
            "DAY",
            "QUANTITY",
            "SALES_VALUE",
            "RETAIL_DISC",
            "COUPON_DISC",
            "COUPON_MATCH_DISC",
        ],
    )
    max_day = int(transactions["DAY"].max())

    rfm = (
        transactions.groupby("household_key")
        .agg(
            last_purchase_day=("DAY", "max"),
            first_purchase_day=("DAY", "min"),
            frequency_baskets=("BASKET_ID", "nunique"),
            monetary_sales=("SALES_VALUE", "sum"),
            total_units=("QUANTITY", "sum"),
            retail_discount=("RETAIL_DISC", "sum"),
            coupon_discount=("COUPON_DISC", "sum"),
            coupon_match_discount=("COUPON_MATCH_DISC", "sum"),
        )
        .reset_index()
    )
    rfm["recency_days"] = max_day - rfm["last_purchase_day"]
    rfm["customer_tenure_days"] = rfm["last_purchase_day"] - rfm["first_purchase_day"] + 1
    rfm["avg_basket_value"] = rfm["monetary_sales"] / rfm["frequency_baskets"].replace(0, np.nan)
    rfm["total_discount_abs"] = (
        rfm[["retail_discount", "coupon_discount", "coupon_match_discount"]].sum(axis=1).abs()
    )
    rfm["discount_to_sales"] = rfm["total_discount_abs"] / rfm["monetary_sales"].replace(0, np.nan)

    rfm["r_score"] = _score_quantiles(rfm["recency_days"], higher_is_better=False)
    rfm["f_score"] = _score_quantiles(rfm["frequency_baskets"], higher_is_better=True)
    rfm["m_score"] = _score_quantiles(rfm["monetary_sales"], higher_is_better=True)
    rfm["rfm_score"] = (
        rfm["r_score"].astype(str) + rfm["f_score"].astype(str) + rfm["m_score"].astype(str)
    )
    rfm["segment"] = rfm.apply(_assign_segment, axis=1)

    demographics = pd.read_csv(demographic_path)
    return rfm.merge(demographics, on="household_key", how="left")


def _top_distribution(df: pd.DataFrame, column: str, top_n: int = 3) -> str:
    values = (
        df[column]
        .fillna("Unknown")
        .astype(str)
        .value_counts(normalize=True)
        .head(top_n)
        .mul(100)
        .round(1)
    )
    return json.dumps(values.to_dict(), ensure_ascii=False)


def summarize_segments(household_rfm: pd.DataFrame) -> pd.DataFrame:
    total_households = household_rfm["household_key"].nunique()
    summary = (
        household_rfm.groupby("segment")
        .agg(
            households=("household_key", "nunique"),
            avg_recency_days=("recency_days", "mean"),
            median_recency_days=("recency_days", "median"),
            avg_frequency_baskets=("frequency_baskets", "mean"),
            median_frequency_baskets=("frequency_baskets", "median"),
            avg_monetary_sales=("monetary_sales", "mean"),
            median_monetary_sales=("monetary_sales", "median"),
            total_sales=("monetary_sales", "sum"),
            avg_basket_value=("avg_basket_value", "mean"),
            avg_discount_to_sales=("discount_to_sales", "mean"),
        )
        .reset_index()
    )
    summary["household_share_pct"] = summary["households"] / total_households * 100

    for column in DEMO_COLUMNS:
        summary[f"top_{column}_distribution"] = summary["segment"].map(
            household_rfm.groupby("segment").apply(lambda group, col=column: _top_distribution(group, col))
        )

    numeric_cols = summary.select_dtypes(include=["number"]).columns
    summary[numeric_cols] = summary[numeric_cols].round(4)
    return summary.sort_values(["total_sales", "households"], ascending=False)


def run(output_path: Path = TABLEAU_DIR / "rfm_segments.csv") -> tuple[pd.DataFrame, pd.DataFrame]:
    TABLEAU_DIR.mkdir(parents=True, exist_ok=True)
    household_rfm = compute_household_rfm()
    segment_summary = summarize_segments(household_rfm)
    segment_summary.to_csv(output_path, index=False)
    return household_rfm, segment_summary


if __name__ == "__main__":
    _, segments = run()
    print(f"Wrote {len(segments)} segment rows to {TABLEAU_DIR / 'rfm_segments.csv'}")
