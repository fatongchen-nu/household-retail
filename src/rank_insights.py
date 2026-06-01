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


def _candidate_insights(packet: dict[str, Any]) -> list[dict[str, Any]]:
    insights: list[dict[str, Any]] = []

    for row in packet["customer_segmentation"]["segments"]:
        insights.append(
            {
                "source": "Customer Segmentation",
                "score": float(row.get("total_sales") or 0),
                "title": f"{row['segment']} contributes {_money(row.get('total_sales', 0))} sales",
                "detail": (
                    f"{row['households']:,} households, avg monetary "
                    f"{_money(row.get('avg_monetary_sales', 0))}, avg frequency "
                    f"{row.get('avg_frequency_baskets', 0):.1f} baskets."
                ),
            }
        )

    for row in packet["promotion_roi_analysis"]["campaign_metrics"]:
        insights.append(
            {
                "source": "Promotion ROI",
                "score": max(float(row.get("incremental_revenue") or 0), 0),
                "title": (
                    f"Campaign {row['campaign']} estimated incremental revenue: "
                    f"{_money(row.get('incremental_revenue', 0))}"
                ),
                "detail": (
                    f"Promotion type {row['promotion_type']}, lift {row.get('lift_pct', 0):.1f}%, "
                    f"redemption rate {float(row.get('coupon_redemption_rate') or 0) * 100:.1f}%."
                ),
            }
        )

    for row in packet["basket_analysis"]["top_rules_by_lift"]:
        insights.append(
            {
                "source": "Basket Analysis",
                "score": float(row.get("lift") or 0) * float(row.get("pair_basket_count") or 0),
                "title": f"{row['item_a']} + {row['item_b']} has lift {row.get('lift', 0):.2f}",
                "detail": (
                    f"Observed in {row.get('pair_basket_count', 0):,} baskets; "
                    f"{row.get('cross_sell_opportunity', '')}."
                ),
            }
        )

    for row in packet["campaign_targeting_feasibility"]["recommendations"]:
        insights.append(
            {
                "source": "Campaign Targeting",
                "score": max(float(row.get("estimated_incremental_revenue") or 0), 0),
                "title": (
                    f"{row['segment']} / campaign {row['campaign']} opportunity: "
                    f"{_money(row.get('estimated_incremental_revenue', 0))}"
                ),
                "detail": (
                    f"{row.get('promotion_type')} offer, lift {row.get('lift_pct', 0):.1f}%, "
                    f"strength {row.get('recommendation_strength')}."
                ),
            }
        )

    coupon_analysis = packet.get("coupon_dependency_analysis", {})
    for row in coupon_analysis.get("segment_coupon_metrics", []):
        incremental = float(row.get("total_post_90d_incremental_vs_pre_90d") or 0)
        stop_subsidy = int(row.get("Stop Subsidy") or 0)
        reduce_deal = int(row.get("Reduce Deal") or 0)
        keep_deal = int(row.get("Keep Deal") or 0)
        insights.append(
            {
                "source": "Coupon Dependency",
                "score": max(incremental, 0) + (stop_subsidy + reduce_deal + keep_deal) * 100,
                "title": (
                    f"{row['segment']} coupon strategy: "
                    f"{row.get('segment_coupon_strategy', 'Maintain selective testing')}"
                ),
                "detail": (
                    f"Post-90d incremental vs pre-90d {_money(incremental)}, "
                    f"repeat rate {float(row.get('post_90d_repeat_rate_among_coupon_users') or 0) * 100:.1f}%, "
                    f"full-price-after-coupon rate "
                    f"{float(row.get('full_price_post_90d_rate_among_coupon_users') or 0) * 100:.1f}%."
                ),
            }
        )

    return sorted(insights, key=lambda row: row["score"], reverse=True)


def rank_insights(
    evidence_path: Path = EVIDENCE_PATH,
    output_path: Path = OUTPUTS_DIR / "insight_ranking.md",
    top_n: int = 30,
) -> list[dict[str, Any]]:
    packet = json.loads(evidence_path.read_text(encoding="utf-8"))
    provider = os.getenv("AI_PROVIDER", "").strip().lower()

    # Real provider interface retained for production wiring:
    #
    # if provider == "claude":
    #     from anthropic import Anthropic
    #     client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    #     response = client.messages.create(
    #         model=os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-latest"),
    #         max_tokens=3000,
    #         messages=[{"role": "user", "content": json.dumps(packet)}],
    #     )
    #     ranked = parse_ai_ranked_response(response.content[0].text)
    # elif provider == "openai":
    #     from openai import OpenAI
    #     client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    #     response = client.responses.create(
    #         model=os.getenv("OPENAI_MODEL", "gpt-4.1"),
    #         input=[{"role": "user", "content": json.dumps(packet)}],
    #     )
    #     ranked = parse_ai_ranked_response(response.output_text)
    # else:
    #     ranked = _candidate_insights(packet)

    ranked = _candidate_insights(packet)
    lines = ["# Ranked Retail Insights", ""]
    lines.append("Mock ranking: insights are sorted by numeric impact fields in the evidence packet.")
    if provider:
        lines.append(f"Configured AI_PROVIDER `{provider}` is ignored while mock mode is active.")
    else:
        lines.append("AI_PROVIDER is not set; running in mock mode.")
    lines.append("")

    for idx, insight in enumerate(ranked[:top_n], start=1):
        lines.extend(
            [
                f"## {idx}. {insight['title']}",
                f"* Source: {insight['source']}",
                f"* Mock impact score: {insight['score']:.4f}",
                f"* Evidence: {insight['detail']}",
                "",
            ]
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return ranked


if __name__ == "__main__":
    output = OUTPUTS_DIR / "insight_ranking.md"
    rank_insights(EVIDENCE_PATH, output)
    print(f"Wrote insight ranking to {output}")
