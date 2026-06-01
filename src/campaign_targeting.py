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


def compute_targeting_recommendations(
    transaction_path: Path = DATA_DIR / "transaction_data.csv",
    campaign_table_path: Path = DATA_DIR / "campaign_table.csv",
    campaign_desc_path: Path = DATA_DIR / "campaign_desc.csv",
    coupon_path: Path = DATA_DIR / "coupon.csv",
    redemption_path: Path = DATA_DIR / "coupon_redempt.csv",
    min_exposed_households: int = 15,
) -> pd.DataFrame:
    household_segments = compute_household_rfm()[["household_key", "segment"]]
    segment_lookup = household_segments.set_index("household_key")["segment"].to_dict()
    segment_sizes = household_segments.groupby("segment")["household_key"].nunique().to_dict()

    transactions = pd.read_csv(
        transaction_path,
        usecols=["household_key", "BASKET_ID", "DAY", "PRODUCT_ID", "SALES_VALUE"],
    )
    transactions["segment"] = transactions["household_key"].map(segment_lookup)
    transactions = transactions.dropna(subset=["segment"])

    campaign_table = pd.read_csv(campaign_table_path)
    campaign_desc = pd.read_csv(campaign_desc_path)
    coupons = pd.read_csv(coupon_path)
    redemptions = pd.read_csv(redemption_path)

    all_households_by_segment = {
        segment: set(values["household_key"].astype(int))
        for segment, values in household_segments.groupby("segment")
    }
    min_day = int(transactions["DAY"].min())
    max_day = int(transactions["DAY"].max())

    rows: list[dict[str, object]] = []
    for campaign in sorted(campaign_desc["CAMPAIGN"].unique()):
        meta = campaign_desc.loc[campaign_desc["CAMPAIGN"] == campaign].iloc[0]
        start_day = int(meta["START_DAY"])
        end_day = min(int(meta["END_DAY"]), max_day)
        if start_day > max_day:
            continue

        window_days = end_day - start_day + 1
        pre_start = max(min_day, start_day - window_days)
        pre_end = start_day - 1
        pre_days = max(pre_end - pre_start + 1, 0)
        pre_scale = _safe_divide(window_days, pre_days) if pre_days else 0.0

        campaign_products = set(coupons.loc[coupons["CAMPAIGN"] == campaign, "PRODUCT_ID"].astype(int))
        if not campaign_products:
            continue

        exposed = set(
            campaign_table.loc[campaign_table["CAMPAIGN"] == campaign, "household_key"].astype(int)
        )
        relevant = transactions[
            transactions["PRODUCT_ID"].isin(campaign_products)
            & transactions["DAY"].between(pre_start, end_day)
        ]
        during = relevant[relevant["DAY"].between(start_day, end_day)]
        pre = relevant[relevant["DAY"].between(pre_start, pre_end)] if pre_days else relevant.iloc[0:0]

        campaign_redemptions = redemptions[redemptions["CAMPAIGN"] == campaign]
        redeeming_households = set(campaign_redemptions["household_key"].astype(int))

        for segment, segment_households in all_households_by_segment.items():
            exposed_segment = exposed & segment_households
            control_segment = segment_households - exposed_segment
            if len(exposed_segment) < min_exposed_households or not control_segment:
                continue

            seg_during = during[during["segment"] == segment]
            seg_pre = pre[pre["segment"] == segment]

            treatment_during = seg_during[seg_during["household_key"].isin(exposed_segment)]
            control_during = seg_during[seg_during["household_key"].isin(control_segment)]
            treatment_pre = seg_pre[seg_pre["household_key"].isin(exposed_segment)]
            control_pre = seg_pre[seg_pre["household_key"].isin(control_segment)]

            treatment_rev_phh = _safe_divide(treatment_during["SALES_VALUE"].sum(), len(exposed_segment))
            control_rev_phh = _safe_divide(control_during["SALES_VALUE"].sum(), len(control_segment))
            treatment_pre_phh = _safe_divide(treatment_pre["SALES_VALUE"].sum(), len(exposed_segment)) * pre_scale
            control_pre_phh = _safe_divide(control_pre["SALES_VALUE"].sum(), len(control_segment)) * pre_scale
            incremental_per_household = (
                treatment_rev_phh - treatment_pre_phh - (control_rev_phh - control_pre_phh)
            )
            estimated_incremental_revenue = incremental_per_household * len(exposed_segment)
            lift_pct = (
                (treatment_rev_phh - control_rev_phh) / control_rev_phh * 100
                if control_rev_phh > 0
                else 0.0
            )
            treatment_buyer_rate = _safe_divide(
                treatment_during["household_key"].nunique(), len(exposed_segment)
            )
            control_buyer_rate = _safe_divide(control_during["household_key"].nunique(), len(control_segment))
            redemption_rate = _safe_divide(len(redeeming_households & exposed_segment), len(exposed_segment))
            targeting_opportunity = (
                estimated_incremental_revenue > 0
                and lift_pct > 0
                and treatment_buyer_rate >= control_buyer_rate
            )

            rows.append(
                {
                    "segment": segment,
                    "campaign": int(campaign),
                    "promotion_type": meta["DESCRIPTION"],
                    "segment_households": segment_sizes[segment],
                    "exposed_households": len(exposed_segment),
                    "control_households": len(control_segment),
                    "campaign_products": len(campaign_products),
                    "treatment_revenue_per_household": treatment_rev_phh,
                    "control_revenue_per_household": control_rev_phh,
                    "treatment_pre_revenue_per_household_scaled": treatment_pre_phh,
                    "control_pre_revenue_per_household_scaled": control_pre_phh,
                    "treatment_buyer_rate": treatment_buyer_rate,
                    "control_buyer_rate": control_buyer_rate,
                    "lift_pct": lift_pct,
                    "incremental_per_household": incremental_per_household,
                    "estimated_incremental_revenue": estimated_incremental_revenue,
                    "coupon_redemption_rate": redemption_rate,
                    "targeting_opportunity_flag": bool(targeting_opportunity),
                    "recommendation_strength": (
                        "High"
                        if targeting_opportunity and lift_pct > 20 and redemption_rate > 0
                        else "Medium"
                        if targeting_opportunity
                        else "Low"
                    ),
                    "targeting_recommendation": (
                        f"Target {segment} with {meta['DESCRIPTION']} style offers"
                        if targeting_opportunity
                        else f"Do not prioritize {segment} for {meta['DESCRIPTION']} style offers"
                    ),
                }
            )

    recommendations = pd.DataFrame(rows)
    numeric_cols = recommendations.select_dtypes(include=["number"]).columns
    recommendations[numeric_cols] = recommendations[numeric_cols].round(6)
    return recommendations.sort_values(
        ["targeting_opportunity_flag", "estimated_incremental_revenue", "lift_pct"], ascending=False
    )


def run(output_path: Path = TABLEAU_DIR / "targeting_recommendation.csv") -> pd.DataFrame:
    TABLEAU_DIR.mkdir(parents=True, exist_ok=True)
    recommendations = compute_targeting_recommendations()
    recommendations.to_csv(output_path, index=False)
    return recommendations


if __name__ == "__main__":
    result = run()
    print(f"Wrote {len(result)} targeting rows to {TABLEAU_DIR / 'targeting_recommendation.csv'}")
