from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from basket_analysis import run as run_basket_analysis
from campaign_targeting import run as run_campaign_targeting
from coupon_dependency import run as run_coupon_dependency
from promotion_roi import run as run_promotion_roi
from rfm_segmentation import run as run_rfm_segmentation


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
TABLEAU_DIR = PROJECT_ROOT / "tableau"


def _json_safe(value: Any) -> Any:
    if pd.isna(value) if not isinstance(value, (list, dict, tuple)) else False:
        return None
    if hasattr(value, "item"):
        return value.item()
    if isinstance(value, dict):
        return {str(key): _json_safe(val) for key, val in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def _records(df: pd.DataFrame, limit: int | None = None) -> list[dict[str, Any]]:
    selected = df if limit is None else df.head(limit)
    return [_json_safe(record) for record in selected.to_dict(orient="records")]


def _file_inventory() -> list[dict[str, Any]]:
    inventory = []
    for path in sorted(DATA_DIR.glob("*.csv")):
        header = pd.read_csv(path, nrows=0)
        inventory.append(
            {
                "file": str(path.relative_to(PROJECT_ROOT)),
                "columns": list(header.columns),
                "size_bytes": path.stat().st_size,
            }
        )
    return inventory


def build_evidence_packet() -> dict[str, Any]:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    TABLEAU_DIR.mkdir(parents=True, exist_ok=True)

    household_rfm, rfm_segments = run_rfm_segmentation()
    promotion_roi = run_promotion_roi()
    basket_affinity = run_basket_analysis()
    targeting = run_campaign_targeting()
    coupon_households, coupon_dependency = run_coupon_dependency()

    transaction_summary = pd.read_csv(
        DATA_DIR / "transaction_data.csv",
        usecols=["household_key", "BASKET_ID", "DAY", "SALES_VALUE", "PRODUCT_ID"],
    )

    positive_campaigns = promotion_roi[promotion_roi["true_incremental_flag"] == True]
    positive_targets = targeting[targeting["targeting_opportunity_flag"] == True]
    keep_or_reduce = coupon_households[
        coupon_households["deal_strategy_recommendation"].isin(["Keep Deal", "Reduce Deal"])
    ]
    stop_subsidy = coupon_households[
        coupon_households["deal_strategy_recommendation"] == "Stop Subsidy"
    ]
    ranked_targets = targeting.sort_values(
        ["targeting_opportunity_flag", "estimated_incremental_revenue", "lift_pct"],
        ascending=[False, False, False],
    )

    packet: dict[str, Any] = {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "project_root": str(PROJECT_ROOT),
            "data_inventory": _file_inventory(),
            "analysis_scope": {
                "households_in_transactions": int(transaction_summary["household_key"].nunique()),
                "baskets": int(transaction_summary["BASKET_ID"].nunique()),
                "products_purchased": int(transaction_summary["PRODUCT_ID"].nunique()),
                "min_day": int(transaction_summary["DAY"].min()),
                "max_day": int(transaction_summary["DAY"].max()),
                "total_sales_value": round(float(transaction_summary["SALES_VALUE"].sum()), 4),
            },
            "methodology_notes": [
                "RFM segments are scored at household level using recency, unique basket frequency, and monetary sales.",
                "Promotion ROI is observational: campaign exposure comes from campaign_table, campaign timing from campaign_desc, and promoted products from coupon.",
                "Incremental revenue uses a difference-in-differences style estimate versus a pre-campaign window and unexposed households.",
                "Basket analysis uses commodity-level association rules over frequent basket items to keep rules interpretable.",
                "Coupon dependency compares household spend before and after first coupon redemption and flags whether later purchases happen at full price or only with deals.",
                "AI outputs are mock-mode renderings of this evidence packet; no external API calls are made.",
            ],
        },
        "customer_segmentation": {
            "tableau_output": str((TABLEAU_DIR / "rfm_segments.csv").relative_to(PROJECT_ROOT)),
            "segment_count": int(rfm_segments["segment"].nunique()),
            "household_count": int(household_rfm["household_key"].nunique()),
            "segments": _records(rfm_segments),
        },
        "promotion_roi_analysis": {
            "tableau_output": str((TABLEAU_DIR / "promotion_roi.csv").relative_to(PROJECT_ROOT)),
            "campaigns_analyzed": int(promotion_roi["campaign"].nunique()),
            "campaigns_with_positive_incremental_flag": int(positive_campaigns["campaign"].nunique()),
            "total_estimated_incremental_revenue": round(
                float(promotion_roi["incremental_revenue"].sum()), 4
            ),
            "positive_incremental_revenue": round(float(positive_campaigns["incremental_revenue"].sum()), 4),
            "top_campaigns_by_incremental_revenue": _records(
                promotion_roi.sort_values("incremental_revenue", ascending=False), 10
            ),
            "campaign_metrics": _records(promotion_roi),
        },
        "basket_analysis": {
            "tableau_output": str((TABLEAU_DIR / "basket_affinity.csv").relative_to(PROJECT_ROOT)),
            "rules_generated": int(len(basket_affinity)),
            "top_rules_by_lift": _records(basket_affinity.sort_values("lift", ascending=False), 25),
            "top_rules_by_support": _records(basket_affinity.sort_values("support", ascending=False), 25),
        },
        "campaign_targeting_feasibility": {
            "tableau_output": str(
                (TABLEAU_DIR / "targeting_recommendation.csv").relative_to(PROJECT_ROOT)
            ),
            "segment_campaign_pairs_analyzed": int(len(targeting)),
            "positive_segment_campaign_pairs": int(len(positive_targets)),
            "estimated_incremental_revenue_positive_pairs": round(
                float(positive_targets["estimated_incremental_revenue"].sum()), 4
            ),
            "top_recommendations": _records(ranked_targets, 25),
            "recommendations": _records(targeting),
        },
        "coupon_dependency_analysis": {
            "tableau_output": str((TABLEAU_DIR / "coupon_dependency.csv").relative_to(PROJECT_ROOT)),
            "household_output": str(
                (TABLEAU_DIR / "coupon_household_scores.csv").relative_to(PROJECT_ROOT)
            ),
            "coupon_households": int(coupon_households["coupon_user_flag"].sum()),
            "households_recommended_keep_or_reduce_deal": int(len(keep_or_reduce)),
            "households_recommended_stop_subsidy": int(len(stop_subsidy)),
            "segment_count": int(coupon_dependency["segment"].nunique()),
            "top_segments_by_post_coupon_incremental": _records(
                coupon_dependency.sort_values(
                    "total_post_90d_incremental_vs_pre_90d", ascending=False
                ),
                10,
            ),
            "segment_coupon_metrics": _records(coupon_dependency),
            "top_households_by_post_coupon_incremental": _records(
                coupon_households[
                    coupon_households["coupon_user_flag"] == True
                ].sort_values("post_90d_incremental_vs_pre_90d", ascending=False),
                25,
            ),
        },
    }
    return packet


def write_evidence_packet(path: Path = OUTPUTS_DIR / "metric_evidence_packet.json") -> dict[str, Any]:
    packet = build_evidence_packet()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(packet, indent=2, ensure_ascii=False), encoding="utf-8")
    return packet


if __name__ == "__main__":
    output = OUTPUTS_DIR / "metric_evidence_packet.json"
    write_evidence_packet(output)
    print(f"Wrote evidence packet to {output}")
