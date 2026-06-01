from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
TABLEAU_DIR = PROJECT_ROOT / "tableau"


def _safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0 or pd.isna(denominator):
        return 0.0
    return float(numerator / denominator)


def _period_metrics(df: pd.DataFrame, households: set[int], all_denominator: int) -> dict[str, float]:
    subset = df[df["household_key"].isin(households)] if households else df.iloc[0:0]
    revenue = float(subset["SALES_VALUE"].sum())
    buyers = int(subset["household_key"].nunique())
    baskets = int(subset["BASKET_ID"].nunique())
    discount = float(
        subset[["RETAIL_DISC", "COUPON_DISC", "COUPON_MATCH_DISC"]].sum(axis=1).abs().sum()
    )
    return {
        "revenue": revenue,
        "buyers": buyers,
        "baskets": baskets,
        "discount_abs": discount,
        "revenue_per_household": _safe_divide(revenue, all_denominator),
        "buyer_rate": _safe_divide(buyers, all_denominator),
    }


def compute_promotion_roi(
    transaction_path: Path = DATA_DIR / "transaction_data.csv",
    campaign_table_path: Path = DATA_DIR / "campaign_table.csv",
    campaign_desc_path: Path = DATA_DIR / "campaign_desc.csv",
    coupon_path: Path = DATA_DIR / "coupon.csv",
    redemption_path: Path = DATA_DIR / "coupon_redempt.csv",
) -> pd.DataFrame:
    transactions = pd.read_csv(
        transaction_path,
        usecols=[
            "household_key",
            "BASKET_ID",
            "DAY",
            "PRODUCT_ID",
            "SALES_VALUE",
            "RETAIL_DISC",
            "COUPON_DISC",
            "COUPON_MATCH_DISC",
        ],
    )
    campaign_table = pd.read_csv(campaign_table_path)
    campaign_desc = pd.read_csv(campaign_desc_path)
    coupons = pd.read_csv(coupon_path)
    redemptions = pd.read_csv(redemption_path)

    all_households = set(transactions["household_key"].unique())
    all_household_count = len(all_households)
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

        exposed_households = set(
            campaign_table.loc[campaign_table["CAMPAIGN"] == campaign, "household_key"].astype(int)
        ) & all_households
        control_households = all_households - exposed_households
        campaign_products = set(coupons.loc[coupons["CAMPAIGN"] == campaign, "PRODUCT_ID"].astype(int))
        if not campaign_products or not exposed_households:
            continue

        relevant = transactions[
            transactions["PRODUCT_ID"].isin(campaign_products)
            & transactions["DAY"].between(pre_start, end_day)
        ]
        during = relevant[relevant["DAY"].between(start_day, end_day)]
        pre = relevant[relevant["DAY"].between(pre_start, pre_end)] if pre_days else relevant.iloc[0:0]

        treatment = _period_metrics(during, exposed_households, len(exposed_households))
        control = _period_metrics(during, control_households, len(control_households))
        treatment_pre = _period_metrics(pre, exposed_households, len(exposed_households))
        control_pre = _period_metrics(pre, control_households, len(control_households))

        treatment_pre_scaled = treatment_pre["revenue_per_household"] * pre_scale
        control_pre_scaled = control_pre["revenue_per_household"] * pre_scale
        did_incremental_per_household = (
            treatment["revenue_per_household"]
            - treatment_pre_scaled
            - (control["revenue_per_household"] - control_pre_scaled)
        )
        incremental_revenue = did_incremental_per_household * len(exposed_households)
        lift_pct = (
            (treatment["revenue_per_household"] - control["revenue_per_household"])
            / control["revenue_per_household"]
            * 100
            if control["revenue_per_household"] > 0
            else 0.0
        )

        campaign_redemptions = redemptions[redemptions["CAMPAIGN"] == campaign]
        redeeming_exposed = set(campaign_redemptions["household_key"].astype(int)) & exposed_households
        redemption_rate = _safe_divide(len(redeeming_exposed), len(exposed_households))
        discount_investment = treatment["discount_abs"]

        rows.append(
            {
                "campaign": int(campaign),
                "promotion_type": meta["DESCRIPTION"],
                "start_day": start_day,
                "end_day": end_day,
                "window_days": window_days,
                "pre_start_day": pre_start if pre_days else np.nan,
                "pre_end_day": pre_end if pre_days else np.nan,
                "all_households": all_household_count,
                "exposed_households": len(exposed_households),
                "control_households": len(control_households),
                "campaign_products": len(campaign_products),
                "treatment_revenue": treatment["revenue"],
                "control_revenue": control["revenue"],
                "treatment_revenue_per_household": treatment["revenue_per_household"],
                "control_revenue_per_household": control["revenue_per_household"],
                "treatment_buyer_rate": treatment["buyer_rate"],
                "control_buyer_rate": control["buyer_rate"],
                "treatment_pre_revenue_per_household_scaled": treatment_pre_scaled,
                "control_pre_revenue_per_household_scaled": control_pre_scaled,
                "lift_pct": lift_pct,
                "incremental_revenue": incremental_revenue,
                "discount_investment": discount_investment,
                "observed_roi": _safe_divide(incremental_revenue, discount_investment),
                "coupon_redeeming_households": len(redeeming_exposed),
                "coupon_redemption_rate": redemption_rate,
                "true_incremental_flag": bool(
                    incremental_revenue > 0
                    and lift_pct > 0
                    and treatment["buyer_rate"] >= control["buyer_rate"]
                ),
            }
        )

    roi = pd.DataFrame(rows)
    numeric_cols = roi.select_dtypes(include=["number"]).columns
    roi[numeric_cols] = roi[numeric_cols].round(6)
    return roi.sort_values("incremental_revenue", ascending=False)


def run(output_path: Path = TABLEAU_DIR / "promotion_roi.csv") -> pd.DataFrame:
    TABLEAU_DIR.mkdir(parents=True, exist_ok=True)
    roi = compute_promotion_roi()
    roi.to_csv(output_path, index=False)
    return roi


if __name__ == "__main__":
    result = run()
    print(f"Wrote {len(result)} campaign rows to {TABLEAU_DIR / 'promotion_roi.csv'}")
