# AI-Assisted Retail Analytics Workflow

This project is a reproducible retail analytics workflow for household segmentation, promotion incrementality, coupon dependency, basket affinity, and campaign targeting, with an AI layer that can explain evidence but never invent metrics.

The key principle is simple: AI can help summarize the analysis, but every number must trace back to the local CSV data and `outputs/metric_evidence_packet.json`.

## Dataset

The project uses local retail transaction and campaign files in `data/`:

```text
data/transaction_data.csv     Household-level purchase records
data/campaign_table.csv       Household campaign exposure table
data/campaign_desc.csv        Campaign metadata and active date windows
data/coupon.csv               Campaign coupon-to-product mappings
data/coupon_redempt.csv       Household coupon redemption records
data/hh_demographic.csv       Household demographic attributes
data/product.csv              Product hierarchy and category metadata
```

`transaction_data.csv` is the core fact table. Campaign ROI is estimated by combining campaign exposure households, campaign date windows, and products attached to each campaign through the coupon table.

## Project Goal

Build a retail analytics workflow that can:

- Segment households with RFM and summarize demographic distributions.
- Compare promoted versus non-promoted buying behavior.
- Estimate campaign lift, incremental revenue, and coupon redemption rate.
- Analyze coupon dependency, post-coupon retention, and whether households should keep receiving deals.
- Identify commodity-level basket affinities and cross-sell opportunities.
- Combine segment behavior and promotion response into targeting recommendations.
- Generate an evidence packet, memo, ranked insights, and a mock natural-language query interface without calling external AI APIs.
- Support Tableau dashboarding with generated CSV extracts and a packaged workbook artifact.

## Repository Structure

```text
/data
/src
/outputs
/tableau
```

- `/data`: Source CSV files.
- `/src`: Deterministic analytics modules and AI-layer mock interfaces.
- `/outputs`: Generated evidence packet, memo, and ranked insight report.
- `/tableau`: Tableau-ready CSV files and dashboard workbook package.

## Source Of Truth

The source of truth is:

```text
outputs/metric_evidence_packet.json
```

Any memo claim, dashboard annotation, recommendation, or insight ranking should trace back to this file or one of the Tableau CSV exports generated from the same pipeline.

## Complete Run Steps

From the project root:

```bash
python -m py_compile src/*.py
python src/build_evidence_packet.py
python src/generate_memo.py
python src/rank_insights.py
```

This creates:

```text
outputs/metric_evidence_packet.json
outputs/retail_memo.md
outputs/insight_ranking.md
tableau/rfm_segments.csv
tableau/promotion_roi.csv
tableau/coupon_dependency.csv
tableau/coupon_household_scores.csv
tableau/basket_affinity.csv
tableau/targeting_recommendation.csv
```

Run the Streamlit dashboard and query interface:

```bash
streamlit run src/query_interface.py --server.headless true --server.port 8501 --server.address 127.0.0.1
```

Open:

```text
http://127.0.0.1:8501
```

Generate the packaged Tableau workbook:

```bash
python src/build_tableau_workbook.py
```

This creates:

```text
tableau/retail_analytics_dashboard.twbx
```

## Core Results Summary

The current deterministic run covers:

- `2,500` households
- `276,484` baskets
- `92,339` purchased products
- `$8,057,463.08` total sales value

Current top findings:

- Largest revenue segment: `Champions`, with `512` households and `$3,685,912.66` observed sales.
- Strongest campaign by estimated incremental revenue: campaign `18`, `TypeA`, with `$4,368.73` estimated incremental revenue and `183.7%` lift.
- Top feasible targeting recommendation: `Big Spenders` for `TypeA` campaign `18`, with `$2,154.41` estimated incremental revenue.
- Coupon dependency readout: `434` households redeemed coupons; `213` are recommended for `Keep Deal`, `29` for `Stop Subsidy`, and `805` dormant/at-risk households are flagged for controlled winback tests.
- Best post-coupon segment readout: `Loyal Customers`, with `$5,568.51` more spend in the 90 days after first coupon redemption than in the prior 90 days.
- Highest-lift basket affinity among top rules: `DRY NOODLES/PASTA + PASTA SAUCE`.

Promotion incrementality is observational. The workflow uses a difference-in-differences style estimate against a pre-campaign window and unexposed households; it should not be interpreted as a randomized experiment.

## Analytics Modules

### Customer Segmentation

Script:

```text
src/rfm_segmentation.py
```

Output:

```text
tableau/rfm_segments.csv
```

The module scores households on recency, basket frequency, and monetary value, then assigns interpretable RFM segments such as `Champions`, `Loyal Customers`, `At Risk High Value`, and `Hibernating`.

### Promotion ROI Analysis

Script:

```text
src/promotion_roi.py
```

Output:

```text
tableau/promotion_roi.csv
```

The module estimates campaign lift, incremental revenue, coupon redemption rate, observed ROI, and a `true_incremental_flag` for campaigns with positive revenue and buyer-rate signals.

### Coupon Dependency & Post-Promotion Retention

Script:

```text
src/coupon_dependency.py
```

Outputs:

```text
tableau/coupon_dependency.csv
tableau/coupon_household_scores.csv
```

The module compares each coupon user's observed spending before and after first coupon redemption. It calculates post-coupon 30/60/90 day spend, repeat purchase flags, full-price-after-coupon behavior, coupon dependency ratio, deal dependency ratio, subsidy efficiency, and a household-level strategy recommendation:

- `Keep Deal`
- `Reduce Deal`
- `Stop Subsidy`
- `Test Smaller Deal`
- `Winback Test`
- `No Deal Needed`

This answers questions like whether a customer keeps buying after using a coupon, only buys on deal, or should receive fewer subsidies.

### Basket Analysis

Script:

```text
src/basket_analysis.py
```

Output:

```text
tableau/basket_affinity.csv
```

The module builds commodity-level association rules with support, confidence, lift, category affinity, and cross-sell recommendation fields.

### Campaign Targeting Feasibility

Script:

```text
src/campaign_targeting.py
```

Output:

```text
tableau/targeting_recommendation.csv
```

The module combines RFM segments and promotion response to identify which segment-campaign pairs are most feasible for targeted promotion.

## Streamlit App

The Streamlit app is designed as a summary dashboard first, with AI inquiry as an analyst-assistant layer below it.

The dashboard includes:

- Headline KPIs for households, baskets, sales, positive campaigns, and targeting opportunities.
- RFM segment distribution chart.
- Promotion ROI ranking chart.
- Coupon strategy mix and post-coupon spend change charts.
- Detail tables for segments, campaign ROI, coupon dependency, basket affinity, and targeting recommendations.
- Mock AI inquiry that answers questions by matching keywords against the evidence packet.

## AI Layer Architecture

The AI layer is designed with two modes:

### Mock Mode

Current behavior uses mock logic only:

- `src/build_evidence_packet.py` builds `outputs/metric_evidence_packet.json`.
- `src/generate_memo.py` reads the evidence packet and writes `outputs/retail_memo.md`.
- `src/rank_insights.py` ranks insights by numeric impact fields in the evidence packet.
- `src/query_interface.py` provides a Streamlit natural-language query UI using keyword matching over the evidence packet.

No external API calls are made in mock mode.

### Live Mode

The scripts keep commented provider interfaces for Claude and OpenAI. A production version can switch providers with:

```bash
export AI_PROVIDER=claude
# or
export AI_PROVIDER=openai
```

The live API blocks are intentionally commented out in this portfolio version. Before enabling them, add API keys through environment variables and keep the same evidence-packet constraint: the model may explain, rank, or format the evidence, but it may not create new numbers.

## Tableau Dashboard

The Tableau package is:

```text
tableau/retail_analytics_dashboard.twbx
```

It includes the Tableau-ready CSV extracts and workbook views for:

- RFM segment distribution
- Promotion ROI ranking
- Coupon dependency / strategy mix
- Basket affinity and targeting recommendation supporting views

The workbook should be opened in Tableau Desktop or Tableau Public for final visual polish if needed. The included CSV files are the canonical dashboard inputs.
