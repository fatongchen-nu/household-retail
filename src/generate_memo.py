from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
EVIDENCE_PATH = OUTPUTS_DIR / "metric_evidence_packet.json"


def _money(value: float | int | None) -> str:
    return "$0.00" if value is None else f"${float(value):,.2f}"


def _pct(value: float | int | None, scale: float = 1.0) -> str:
    return "0.0%" if value is None else f"{float(value) * scale:.1f}%"


def _format_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    if not rows:
        return "_No rows available._"
    header = "| " + " | ".join(columns) + " |"
    divider = "| " + " | ".join(["---"] * len(columns)) + " |"
    lines = [header, divider]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(col, "")) for col in columns) + " |")
    return "\n".join(lines)


def generate_mock_memo(packet: dict[str, Any]) -> str:
    scope = packet["metadata"]["analysis_scope"]
    segments = packet["customer_segmentation"]["segments"]
    campaigns = packet["promotion_roi_analysis"]["top_campaigns_by_incremental_revenue"]
    baskets = packet["basket_analysis"]["top_rules_by_lift"]
    targets = packet["campaign_targeting_feasibility"]["top_recommendations"]
    coupon_segments = packet.get("coupon_dependency_analysis", {}).get(
        "top_segments_by_post_coupon_incremental", []
    )

    top_segment = max(segments, key=lambda row: row["total_sales"]) if segments else {}
    top_campaign = campaigns[0] if campaigns else {}
    top_target = targets[0] if targets else {}
    top_coupon_segment = coupon_segments[0] if coupon_segments else {}

    memo = [
        "# AI-Assisted Retail Analytics Memo",
        "",
        "## Executive Summary",
        (
            f"The analysis covers {scope['households_in_transactions']:,} households, "
            f"{scope['baskets']:,} baskets, {scope['products_purchased']:,} purchased products, "
            f"and {_money(scope['total_sales_value'])} in sales value."
        ),
        (
            f"The largest revenue segment is **{top_segment.get('segment', 'N/A')}** with "
            f"{int(top_segment.get('households', 0)):,} households and "
            f"{_money(top_segment.get('total_sales', 0))} in observed sales."
        ),
        (
            f"The strongest campaign by estimated incremental revenue is campaign "
            f"**{top_campaign.get('campaign', 'N/A')}** "
            f"({_money(top_campaign.get('incremental_revenue', 0))}, "
            f"lift {top_campaign.get('lift_pct', 0):.1f}%)."
        ),
        (
            f"The top targeting opportunity is **{top_target.get('segment', 'N/A')} / "
            f"{top_target.get('promotion_type', 'N/A')} campaign {top_target.get('campaign', 'N/A')}** "
            f"with {_money(top_target.get('estimated_incremental_revenue', 0))} estimated incremental revenue."
        ),
        (
            f"Coupon dependency analysis suggests **{top_coupon_segment.get('segment', 'N/A')}** has the "
            f"largest post-coupon spend improvement versus the prior 90 days "
            f"({_money(top_coupon_segment.get('total_post_90d_incremental_vs_pre_90d', 0))}); "
            f"segment strategy: {top_coupon_segment.get('segment_coupon_strategy', 'N/A')}."
        ),
        "",
        "## Customer Segmentation",
        _format_table(
            segments,
            [
                "segment",
                "households",
                "household_share_pct",
                "avg_recency_days",
                "avg_frequency_baskets",
                "avg_monetary_sales",
                "total_sales",
            ],
        ),
        "",
        "## Promotion ROI",
        _format_table(
            campaigns[:10],
            [
                "campaign",
                "promotion_type",
                "exposed_households",
                "lift_pct",
                "incremental_revenue",
                "coupon_redemption_rate",
                "true_incremental_flag",
            ],
        ),
        "",
        "## Basket Analysis",
        _format_table(
            baskets[:10],
            [
                "item_a",
                "item_b",
                "pair_basket_count",
                "support",
                "confidence_a_to_b",
                "confidence_b_to_a",
                "lift",
                "cross_sell_opportunity",
            ],
        ),
        "",
        "## Campaign Targeting Feasibility",
        _format_table(
            targets[:10],
            [
                "segment",
                "campaign",
                "promotion_type",
                "exposed_households",
                "lift_pct",
                "estimated_incremental_revenue",
                "coupon_redemption_rate",
                "recommendation_strength",
            ],
        ),
        "",
        "## Coupon Dependency & Post-Promotion Retention",
        _format_table(
            coupon_segments[:10],
            [
                "segment",
                "coupon_households",
                "coupon_user_rate",
                "avg_coupon_dependency_ratio",
                "avg_deal_dependency_ratio",
                "post_90d_repeat_rate_among_coupon_users",
                "full_price_post_90d_rate_among_coupon_users",
                "total_post_90d_incremental_vs_pre_90d",
                "segment_coupon_strategy",
            ],
        ),
        "",
        "## Method Notes",
        "* All numbers are read from `metric_evidence_packet.json`, which is built from local CSV files.",
        "* The AI layer is running in mock mode and does not call external APIs.",
        "* Promotion incrementality is observational, not a randomized experiment result.",
        "* Coupon dependency is based on observed pre/post purchase behavior, not randomized deal holdouts.",
    ]
    return "\n".join(memo)


def generate_memo(
    evidence_path: Path = EVIDENCE_PATH,
    output_path: Path = OUTPUTS_DIR / "retail_memo.md",
) -> str:
    packet = json.loads(evidence_path.read_text(encoding="utf-8"))
    provider = os.getenv("AI_PROVIDER", "").strip().lower()

    # Real provider interface retained for production wiring:
    #
    # if provider == "claude":
    #     from anthropic import Anthropic
    #     client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    #     response = client.messages.create(
    #         model=os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-latest"),
    #         max_tokens=4000,
    #         messages=[{"role": "user", "content": json.dumps(packet)}],
    #     )
    #     memo = response.content[0].text
    # elif provider == "openai":
    #     from openai import OpenAI
    #     client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    #     response = client.responses.create(
    #         model=os.getenv("OPENAI_MODEL", "gpt-4.1"),
    #         input=[{"role": "user", "content": json.dumps(packet)}],
    #     )
    #     memo = response.output_text
    # else:
    #     memo = generate_mock_memo(packet)

    memo = generate_mock_memo(packet)
    if provider:
        memo += f"\n\n_Mock mode active. Configured AI_PROVIDER: `{provider}`._\n"
    else:
        memo += "\n\n_Mock mode active. `AI_PROVIDER` is not set._\n"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(memo, encoding="utf-8")
    return memo


if __name__ == "__main__":
    output = OUTPUTS_DIR / "retail_memo.md"
    generate_memo(EVIDENCE_PATH, output)
    print(f"Wrote memo to {output}")
