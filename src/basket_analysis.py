from __future__ import annotations

from collections import Counter
from itertools import combinations
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
TABLEAU_DIR = PROJECT_ROOT / "tableau"


def compute_basket_affinity(
    transaction_path: Path = DATA_DIR / "transaction_data.csv",
    product_path: Path = DATA_DIR / "product.csv",
    top_n_items: int = 120,
    min_pair_count: int = 75,
    max_basket_items: int = 40,
) -> pd.DataFrame:
    transactions = pd.read_csv(transaction_path, usecols=["BASKET_ID", "PRODUCT_ID", "SALES_VALUE"])
    products = pd.read_csv(
        product_path,
        usecols=["PRODUCT_ID", "DEPARTMENT", "COMMODITY_DESC"],
    )
    merged = transactions.merge(products, on="PRODUCT_ID", how="left")
    merged["COMMODITY_DESC"] = merged["COMMODITY_DESC"].fillna("UNKNOWN")
    merged["DEPARTMENT"] = merged["DEPARTMENT"].fillna("UNKNOWN")

    item_basket_counts = (
        merged.drop_duplicates(["BASKET_ID", "COMMODITY_DESC"])
        .groupby("COMMODITY_DESC")["BASKET_ID"]
        .nunique()
        .sort_values(ascending=False)
    )
    top_items = set(item_basket_counts.head(top_n_items).index)
    filtered = merged[merged["COMMODITY_DESC"].isin(top_items)]

    basket_items = (
        filtered.drop_duplicates(["BASKET_ID", "COMMODITY_DESC"])
        .groupby("BASKET_ID")["COMMODITY_DESC"]
        .apply(lambda values: sorted(set(values)))
    )
    basket_items = basket_items[basket_items.map(lambda values: 2 <= len(values) <= max_basket_items)]
    basket_count = len(basket_items)

    item_counts: Counter[str] = Counter()
    pair_counts: Counter[tuple[str, str]] = Counter()
    for items in basket_items:
        item_counts.update(items)
        pair_counts.update(combinations(items, 2))

    department_lookup = (
        merged.dropna(subset=["COMMODITY_DESC"])
        .groupby("COMMODITY_DESC")["DEPARTMENT"]
        .agg(lambda values: values.value_counts().index[0])
        .to_dict()
    )

    rows: list[dict[str, object]] = []
    for (item_a, item_b), pair_count in pair_counts.items():
        if pair_count < min_pair_count:
            continue
        support = pair_count / basket_count
        support_a = item_counts[item_a] / basket_count
        support_b = item_counts[item_b] / basket_count
        confidence_a_to_b = pair_count / item_counts[item_a]
        confidence_b_to_a = pair_count / item_counts[item_b]
        lift = support / (support_a * support_b) if support_a and support_b else 0.0

        if confidence_a_to_b >= confidence_b_to_a:
            cross_sell = f"Recommend {item_b} to baskets containing {item_a}"
            anchor_item = item_a
            recommended_item = item_b
            recommendation_confidence = confidence_a_to_b
        else:
            cross_sell = f"Recommend {item_a} to baskets containing {item_b}"
            anchor_item = item_b
            recommended_item = item_a
            recommendation_confidence = confidence_b_to_a

        rows.append(
            {
                "item_a": item_a,
                "item_b": item_b,
                "department_a": department_lookup.get(item_a, "UNKNOWN"),
                "department_b": department_lookup.get(item_b, "UNKNOWN"),
                "basket_count": basket_count,
                "pair_basket_count": pair_count,
                "support": support,
                "confidence_a_to_b": confidence_a_to_b,
                "confidence_b_to_a": confidence_b_to_a,
                "lift": lift,
                "category_affinity": f"{item_a} + {item_b}",
                "anchor_item": anchor_item,
                "recommended_item": recommended_item,
                "recommendation_confidence": recommendation_confidence,
                "cross_sell_opportunity": cross_sell,
            }
        )

    affinity = pd.DataFrame(rows)
    numeric_cols = affinity.select_dtypes(include=["number"]).columns
    affinity[numeric_cols] = affinity[numeric_cols].round(6)
    return affinity.sort_values(["lift", "pair_basket_count"], ascending=False)


def run(output_path: Path = TABLEAU_DIR / "basket_affinity.csv") -> pd.DataFrame:
    TABLEAU_DIR.mkdir(parents=True, exist_ok=True)
    affinity = compute_basket_affinity()
    affinity.to_csv(output_path, index=False)
    return affinity


if __name__ == "__main__":
    result = run()
    print(f"Wrote {len(result)} basket affinity rows to {TABLEAU_DIR / 'basket_affinity.csv'}")
