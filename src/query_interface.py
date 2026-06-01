from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
TABLEAU_DIR = PROJECT_ROOT / "tableau"
EVIDENCE_PATH = OUTPUTS_DIR / "metric_evidence_packet.json"


@st.cache_data
def _load_packet() -> dict[str, Any]:
    if not EVIDENCE_PATH.exists():
        return {
            "error": (
                "metric_evidence_packet.json not found. "
                "Run `python src/build_evidence_packet.py` first."
            )
        }
    return json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))


@st.cache_data
def _load_tableau_csvs() -> dict[str, pd.DataFrame]:
    return {
        "rfm": pd.read_csv(TABLEAU_DIR / "rfm_segments.csv"),
        "promotion": pd.read_csv(TABLEAU_DIR / "promotion_roi.csv"),
        "basket": pd.read_csv(TABLEAU_DIR / "basket_affinity.csv"),
        "targeting": pd.read_csv(TABLEAU_DIR / "targeting_recommendation.csv"),
        "coupon": pd.read_csv(TABLEAU_DIR / "coupon_dependency.csv"),
    }


def _money(value: float | int | None) -> str:
    return "$0.00" if value is None else f"${float(value):,.2f}"


def _pct(value: float | int | None, scale: float = 1.0) -> str:
    return "0.0%" if value is None else f"{float(value) * scale:.1f}%"


def _mock_answer(question: str, packet: dict[str, Any]) -> tuple[str, str, Any]:
    query = question.lower()
    if "error" in packet:
        return "Missing evidence packet", packet["error"], {}

    if any(keyword in query for keyword in ["segment", "rfm", "customer", "household", "人口", "分群", "客户"]):
        rows = packet["customer_segmentation"]["segments"]
        top = max(rows, key=lambda row: row["total_sales"])
        answer = (
            f"The leading segment is **{top['segment']}** with {top['households']:,} households, "
            f"{_money(top['total_sales'])} total sales, and average monetary value "
            f"{_money(top['avg_monetary_sales'])}."
        )
        return "Customer Segmentation", answer, rows

    if any(
        keyword in query
        for keyword in [
            "dependency",
            "retention",
            "post coupon",
            "deal only",
            "subsidy",
            "coupon dependency",
            "用券后",
            "依赖",
            "补贴",
            "放弃",
            "少发",
        ]
    ):
        rows = packet.get("coupon_dependency_analysis", {}).get(
            "top_segments_by_post_coupon_incremental", []
        )
        top = rows[0] if rows else {}
        answer = (
            f"The strongest post-coupon segment is **{top.get('segment', 'N/A')}** with "
            f"{_money(top.get('total_post_90d_incremental_vs_pre_90d', 0))} post-90d spend "
            f"improvement versus the prior 90 days. Strategy: "
            f"**{top.get('segment_coupon_strategy', 'N/A')}**. "
            f"Full-price-after-coupon rate is "
            f"{_pct(top.get('full_price_post_90d_rate_among_coupon_users', 0), 100)}."
        )
        return "Coupon Dependency", answer, rows

    if any(keyword in query for keyword in ["promotion", "campaign", "coupon", "roi", "lift", "促销", "优惠券"]):
        rows = packet["promotion_roi_analysis"]["top_campaigns_by_incremental_revenue"]
        top = rows[0]
        answer = (
            f"Campaign **{top['campaign']}** ({top['promotion_type']}) has the highest estimated "
            f"incremental revenue at {_money(top['incremental_revenue'])}, with "
            f"{top['lift_pct']:.1f}% lift and {_pct(top['coupon_redemption_rate'], 100)} coupon redemption."
        )
        return "Promotion ROI", answer, rows

    if any(keyword in query for keyword in ["basket", "cross", "sell", "affinity", "association", "共购", "篮子"]):
        rows = packet["basket_analysis"]["top_rules_by_lift"]
        top = rows[0]
        answer = (
            f"The strongest basket affinity is **{top['item_a']} + {top['item_b']}** with "
            f"lift {top['lift']:.2f}, observed in {top['pair_basket_count']:,} baskets. "
            f"Suggested action: {top['cross_sell_opportunity']}."
        )
        return "Basket Analysis", answer, rows

    if any(keyword in query for keyword in ["target", "recommend", "sensitive", "incremental", "定向", "推荐", "敏感"]):
        rows = packet["campaign_targeting_feasibility"]["top_recommendations"]
        top = rows[0]
        answer = (
            f"The top targeting opportunity is **{top['segment']} / campaign {top['campaign']}** "
            f"({top['promotion_type']}), with estimated incremental revenue "
            f"{_money(top['estimated_incremental_revenue'])} and {top['lift_pct']:.1f}% lift."
        )
        return "Campaign Targeting", answer, rows

    scope = packet["metadata"]["analysis_scope"]
    answer = (
        f"This evidence packet covers {scope['households_in_transactions']:,} households, "
        f"{scope['baskets']:,} baskets, {scope['products_purchased']:,} purchased products, "
        f"and {_money(scope['total_sales_value'])} total sales."
    )
    return "Evidence Packet Summary", answer, {
        "metadata": scope,
        "customer_segments": packet["customer_segmentation"]["segment_count"],
        "campaigns_analyzed": packet["promotion_roi_analysis"]["campaigns_analyzed"],
        "basket_rules_generated": packet["basket_analysis"]["rules_generated"],
        "targeting_pairs": packet["campaign_targeting_feasibility"]["segment_campaign_pairs_analyzed"],
    }


def _render_kpis(packet: dict[str, Any], tables: dict[str, pd.DataFrame]) -> None:
    scope = packet["metadata"]["analysis_scope"]
    positive_campaigns = int(tables["promotion"]["true_incremental_flag"].sum())
    positive_targets = int(tables["targeting"]["targeting_opportunity_flag"].sum())
    stop_subsidy = int(tables["coupon"].get("Stop Subsidy", pd.Series(dtype=int)).sum())

    cols = st.columns(6)
    cols[0].metric("Households", f"{scope['households_in_transactions']:,}")
    cols[1].metric("Baskets", f"{scope['baskets']:,}")
    cols[2].metric("Total Sales", _money(scope["total_sales_value"]))
    cols[3].metric("Positive Campaigns", f"{positive_campaigns:,}")
    cols[4].metric("Targeting Opportunities", f"{positive_targets:,}")
    cols[5].metric("Stop Subsidy HHs", f"{stop_subsidy:,}")


def _render_summary_dashboard(packet: dict[str, Any], tables: dict[str, pd.DataFrame]) -> None:
    st.subheader("Summary Dashboard")
    _render_kpis(packet, tables)

    rfm = tables["rfm"].sort_values("households", ascending=False)
    promotion = tables["promotion"].sort_values("incremental_revenue", ascending=False).head(12).copy()
    promotion["campaign"] = promotion["campaign"].astype(str)
    basket = tables["basket"].sort_values("lift", ascending=False).head(10)
    targeting = tables["targeting"].sort_values(
        ["targeting_opportunity_flag", "estimated_incremental_revenue"],
        ascending=[False, False],
    ).head(10)
    coupon = tables["coupon"].sort_values(
        "total_post_90d_incremental_vs_pre_90d", ascending=False
    )

    left, right = st.columns(2)
    with left:
        fig = px.bar(
            rfm,
            x="segment",
            y="households",
            color="segment",
            title="RFM Segment Distribution",
            text="households",
        )
        fig.update_layout(showlegend=False, xaxis_title=None, yaxis_title="Households")
        st.plotly_chart(fig, use_container_width=True)

    with right:
        fig = px.bar(
            promotion,
            x="incremental_revenue",
            y="campaign",
            color="promotion_type",
            orientation="h",
            title="Promotion ROI Ranking",
            hover_data=["lift_pct", "coupon_redemption_rate", "true_incremental_flag"],
        )
        fig.update_layout(yaxis_title="Campaign", xaxis_title="Estimated Incremental Revenue")
        st.plotly_chart(fig, use_container_width=True)

    left, right = st.columns(2)
    with left:
        fig = px.bar(
            coupon,
            x="segment",
            y=[
                "Keep Deal",
                "Reduce Deal",
                "Stop Subsidy",
                "Winback Test",
            ],
            title="Coupon Strategy Mix by Segment",
        )
        fig.update_layout(xaxis_title=None, yaxis_title="Households", legend_title="Strategy")
        st.plotly_chart(fig, use_container_width=True)
    with right:
        fig = px.bar(
            coupon,
            x="total_post_90d_incremental_vs_pre_90d",
            y="segment",
            color="segment_coupon_strategy",
            orientation="h",
            title="Post-Coupon 90d Spend Change vs Prior 90d",
            hover_data=[
                "coupon_households",
                "post_90d_repeat_rate_among_coupon_users",
                "full_price_post_90d_rate_among_coupon_users",
            ],
        )
        fig.update_layout(yaxis_title=None, xaxis_title="Post 90d - Pre 90d Sales")
        st.plotly_chart(fig, use_container_width=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["Segments", "Promotion ROI", "Coupon Dependency", "Basket Affinity", "Targeting"]
    )
    with tab1:
        st.dataframe(
            rfm[
                [
                    "segment",
                    "households",
                    "household_share_pct",
                    "avg_recency_days",
                    "avg_frequency_baskets",
                    "avg_monetary_sales",
                    "total_sales",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )
    with tab2:
        st.dataframe(
            promotion[
                [
                    "campaign",
                    "promotion_type",
                    "exposed_households",
                    "lift_pct",
                    "incremental_revenue",
                    "observed_roi",
                    "coupon_redemption_rate",
                    "true_incremental_flag",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )
    with tab3:
        st.dataframe(
            coupon[
                [
                    "segment",
                    "households",
                    "coupon_households",
                    "coupon_user_rate",
                    "avg_coupon_dependency_ratio",
                    "avg_deal_dependency_ratio",
                    "post_90d_repeat_rate_among_coupon_users",
                    "full_price_post_90d_rate_among_coupon_users",
                    "total_post_90d_incremental_vs_pre_90d",
                    "Keep Deal",
                    "Reduce Deal",
                    "Stop Subsidy",
                    "Winback Test",
                    "segment_coupon_strategy",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )
    with tab4:
        st.dataframe(
            basket[
                [
                    "item_a",
                    "item_b",
                    "pair_basket_count",
                    "support",
                    "confidence_a_to_b",
                    "confidence_b_to_a",
                    "lift",
                    "cross_sell_opportunity",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )
    with tab5:
        st.dataframe(
            targeting[
                [
                    "segment",
                    "campaign",
                    "promotion_type",
                    "lift_pct",
                    "estimated_incremental_revenue",
                    "coupon_redemption_rate",
                    "recommendation_strength",
                    "targeting_recommendation",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )


def _render_ai_inquiry(packet: dict[str, Any]) -> None:
    st.subheader("AI Inquiry")
    st.caption("Mock mode: keyword matching over the evidence packet. No external AI API is called.")

    examples = [
        "Which segment has the highest sales?",
        "Which campaign has the best ROI?",
        "Should we keep giving coupons or reduce deal frequency?",
        "What are the strongest basket cross-sell opportunities?",
        "Which segment should we target with promotions?",
    ]
    selected_example = st.selectbox("Example questions", [""] + examples)
    question = st.text_input(
        "Ask a question about the retail analytics evidence packet",
        value=selected_example,
    )

    if question:
        # Real provider interface retained for production wiring:
        #
        # if os.getenv("AI_PROVIDER", "").strip().lower() == "claude":
        #     from anthropic import Anthropic
        #     client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        #     response = client.messages.create(
        #         model=os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-latest"),
        #         max_tokens=1500,
        #         messages=[
        #             {
        #                 "role": "user",
        #                 "content": f"Evidence: {json.dumps(packet)}\nQuestion: {question}",
        #             }
        #         ],
        #     )
        #     st.write(response.content[0].text)
        # elif os.getenv("AI_PROVIDER", "").strip().lower() == "openai":
        #     from openai import OpenAI
        #     client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        #     response = client.responses.create(
        #         model=os.getenv("OPENAI_MODEL", "gpt-4.1"),
        #         input=[
        #             {
        #                 "role": "user",
        #                 "content": f"Evidence: {json.dumps(packet)}\nQuestion: {question}",
        #             }
        #         ],
        #     )
        #     st.write(response.output_text)
        # else:
        #     title, answer, evidence = _mock_answer(question, packet)
        #     st.markdown(answer)
        #     with st.expander("Show matched evidence"):
        #         st.json(evidence)

        title, answer, evidence = _mock_answer(question, packet)
        st.markdown(f"**{title}**")
        st.markdown(answer)
        with st.expander("Show matched evidence"):
            st.json(evidence)


def main() -> None:
    st.set_page_config(page_title="Retail Analytics Dashboard", layout="wide")
    st.title("AI-Assisted Retail Analytics")

    provider = os.getenv("AI_PROVIDER", "").strip().lower()
    if not provider:
        st.info("AI_PROVIDER not set, running in mock mode")
    else:
        st.info(f"AI_PROVIDER={provider}, running in mock mode")

    packet = _load_packet()
    if "error" in packet:
        st.error(packet["error"])
        return

    tables = _load_tableau_csvs()
    _render_summary_dashboard(packet, tables)
    st.divider()
    _render_ai_inquiry(packet)


if __name__ == "__main__":
    main()
