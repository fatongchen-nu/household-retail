# AI-Assisted Retail Analytics Memo

## Executive Summary
The analysis covers 2,500 households, 276,484 baskets, 92,339 purchased products, and $8,057,463.08 in sales value.
The largest revenue segment is **Champions** with 512 households and $3,685,912.66 in observed sales.
The strongest campaign by estimated incremental revenue is campaign **18** ($4,368.73, lift 183.7%).
The top targeting opportunity is **Big Spenders / TypeA campaign 18** with $2,154.41 estimated incremental revenue.
Coupon dependency analysis suggests **Loyal Customers** has the largest post-coupon spend improvement versus the prior 90 days ($5,568.51); segment strategy: Continue targeted deals.

## Customer Segmentation
| segment | households | household_share_pct | avg_recency_days | avg_frequency_baskets | avg_monetary_sales | total_sales |
| --- | --- | --- | --- | --- | --- | --- |
| Champions | 512 | 20.48 | 1.1055 | 245.2383 | 7199.0482 | 3685912.66 |
| Loyal Customers | 325 | 13.0 | 4.0154 | 163.0154 | 4076.7721 | 1324950.93 |
| At Risk High Value | 229 | 9.16 | 33.0568 | 137.262 | 4108.2496 | 940789.16 |
| Needs Attention | 448 | 17.92 | 13.4866 | 58.8571 | 1667.1591 | 746887.27 |
| Potential Loyalists | 302 | 12.08 | 1.3444 | 65.6623 | 2225.1141 | 671984.47 |
| Hibernating | 633 | 25.32 | 75.2259 | 28.2891 | 808.4522 | 511750.24 |
| Big Spenders | 23 | 0.92 | 18.4348 | 81.3913 | 6917.15 | 159094.45 |
| New or Recent | 28 | 1.12 | 0.1429 | 19.0 | 574.7821 | 16093.9 |

## Promotion ROI
| campaign | promotion_type | exposed_households | lift_pct | incremental_revenue | coupon_redemption_rate | true_incremental_flag |
| --- | --- | --- | --- | --- | --- | --- |
| 18 | TypeA | 1133 | 183.694418 | 4368.734038 | 0.188879 | True |
| 26 | TypeA | 332 | 91.63357 | 590.713081 | 0.093373 | True |
| 19 | TypeB | 130 | 1687.846249 | 332.71097 | 0.115385 | True |
| 30 | TypeA | 361 | 78.150756 | 246.382375 | 0.099723 | True |
| 29 | TypeB | 118 | 211.429469 | 196.556524 | 0.110169 | True |
| 25 | TypeB | 187 | 242.296316 | 181.719045 | 0.128342 | True |
| 16 | TypeB | 188 | 560.16453 | 143.890398 | 0.101064 | True |
| 23 | TypeB | 183 | 383.424273 | 118.855114 | 0.125683 | True |
| 12 | TypeB | 170 | 167.667309 | 109.425794 | 0.064706 | True |
| 20 | TypeC | 244 | 252.915327 | 101.509716 | 0.081967 | True |

## Basket Analysis
| item_a | item_b | pair_basket_count | support | confidence_a_to_b | confidence_b_to_a | lift | cross_sell_opportunity |
| --- | --- | --- | --- | --- | --- | --- | --- |
| DRY NOODLES/PASTA | PASTA SAUCE | 6078 | 0.031729 | 0.451661 | 0.542243 | 7.718851 | Recommend DRY NOODLES/PASTA to baskets containing PASTA SAUCE |
| CHEESES | DELI MEATS | 6925 | 0.03615 | 0.628745 | 0.417496 | 7.261293 | Recommend DELI MEATS to baskets containing CHEESES |
| HAIR CARE PRODUCTS | SOAP - LIQUID & BAR | 1321 | 0.006896 | 0.183142 | 0.240883 | 6.397297 | Recommend HAIR CARE PRODUCTS to baskets containing SOAP - LIQUID & BAR |
| MUSHROOMS | PEPPERS-ALL | 1118 | 0.005836 | 0.243732 | 0.140452 | 5.865528 | Recommend PEPPERS-ALL to baskets containing MUSHROOMS |
| ORGANICS FRUIT & VEGETABLES | REFRIGERATED | 746 | 0.003894 | 0.144967 | 0.153435 | 5.711645 | Recommend ORGANICS FRUIT & VEGETABLES to baskets containing REFRIGERATED |
| FROZEN BREAD/DOUGH | PASTA SAUCE | 2257 | 0.011782 | 0.332695 | 0.201356 | 5.685726 | Recommend PASTA SAUCE to baskets containing FROZEN BREAD/DOUGH |
| BEANS - CANNED GLASS & MW | DRY SAUCES/GRAVY | 1653 | 0.008629 | 0.181908 | 0.268868 | 5.667944 | Recommend BEANS - CANNED GLASS & MW to baskets containing DRY SAUCES/GRAVY |
| MUSHROOMS | ORGANICS FRUIT & VEGETABLES | 678 | 0.003539 | 0.147809 | 0.131753 | 5.502224 | Recommend ORGANICS FRUIT & VEGETABLES to baskets containing MUSHROOMS |
| DISHWASH DETERGENTS | HOUSEHOLD CLEANG NEEDS | 1141 | 0.005956 | 0.194776 | 0.166984 | 5.460494 | Recommend HOUSEHOLD CLEANG NEEDS to baskets containing DISHWASH DETERGENTS |
| DRY MIX DESSERTS | FROZEN PIE/DESSERTS | 897 | 0.004683 | 0.173905 | 0.145877 | 5.417684 | Recommend FROZEN PIE/DESSERTS to baskets containing DRY MIX DESSERTS |

## Campaign Targeting Feasibility
| segment | campaign | promotion_type | exposed_households | lift_pct | estimated_incremental_revenue | coupon_redemption_rate | recommendation_strength |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Big Spenders | 18 | TypeA | 19 | 66.99311 | 2154.41 | 0.263158 | High |
| Loyal Customers | 8 | TypeA | 225 | 68.043965 | 1216.775 | 0.142222 | High |
| Loyal Customers | 13 | TypeA | 248 | 43.625922 | 890.060909 | 0.197581 | High |
| Champions | 5 | TypeB | 79 | 1347.314639 | 296.826028 | 0.063291 | High |
| Potential Loyalists | 13 | TypeA | 72 | 99.008163 | 237.797652 | 0.152778 | High |
| Champions | 30 | TypeA | 120 | 1.592644 | 215.525714 | 0.15 | Medium |
| Loyal Customers | 30 | TypeA | 73 | 72.362226 | 213.174722 | 0.123288 | High |
| Champions | 25 | TypeB | 117 | 80.535013 | 178.82881 | 0.162393 | High |
| Potential Loyalists | 8 | TypeA | 85 | 101.118868 | 173.080553 | 0.094118 | High |
| Champions | 19 | TypeB | 64 | 778.129981 | 170.285714 | 0.171875 | High |

## Coupon Dependency & Post-Promotion Retention
| segment | coupon_households | coupon_user_rate | avg_coupon_dependency_ratio | avg_deal_dependency_ratio | post_90d_repeat_rate_among_coupon_users | full_price_post_90d_rate_among_coupon_users | total_post_90d_incremental_vs_pre_90d | segment_coupon_strategy |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Loyal Customers | 91 | 0.28 | 0.015079 | 0.503575 | 1.0 | 1.0 | 5568.51 | Continue targeted deals |
| Potential Loyalists | 35 | 0.115894 | 0.012713 | 0.496371 | 1.0 | 1.0 | 484.86 | Continue targeted deals |
| Hibernating | 6 | 0.009479 | 0.009211 | 0.490697 | 1.0 | 1.0 | 326.72 | Run controlled winback test |
| New or Recent | 0 | 0.0 | 0.007847 | 0.499617 | 0.0 | 0.0 | 0.0 | No coupon readout yet |
| Big Spenders | 10 | 0.434783 | 0.017117 | 0.466999 | 1.0 | 1.0 | -138.01 | Continue targeted deals |
| Needs Attention | 21 | 0.046875 | 0.011323 | 0.487805 | 1.0 | 1.0 | -219.67 | Continue targeted deals |
| At Risk High Value | 51 | 0.222707 | 0.014152 | 0.509116 | 1.0 | 1.0 | -3632.37 | Run controlled winback test |
| Champions | 220 | 0.429688 | 0.017147 | 0.524933 | 1.0 | 1.0 | -4748.2 | Continue targeted deals |

## Method Notes
* All numbers are read from `metric_evidence_packet.json`, which is built from local CSV files.
* The AI layer is running in mock mode and does not call external APIs.
* Promotion incrementality is observational, not a randomized experiment result.
* Coupon dependency is based on observed pre/post purchase behavior, not randomized deal holdouts.

_Mock mode active. `AI_PROVIDER` is not set._
