"""
Generate a realistic synthetic sales dataset for Project 1.

Outputs four CSV files that mimic the schema of a typical e-commerce
data warehouse star schema:
    - customers.csv
    - products.csv
    - orders.csv
    - order_items.csv

Run from repo root:
    python project_1_sales_analysis/scripts/generate_data.py
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

rng = np.random.default_rng(SEED)

# ---------------------------------------------------------------------------
# Reference dimensions
# ---------------------------------------------------------------------------
REGIONS = {
    "North America": ["United States", "Canada", "Mexico"],
    "Europe":        ["United Kingdom", "Germany", "France", "Spain", "Italy"],
    "APAC":          ["Japan", "Australia", "Singapore", "India"],
    "LATAM":         ["Brazil", "Argentina", "Chile"],
}

CATEGORIES = {
    "Electronics": ["Laptop", "Smartphone", "Headphones", "Tablet", "Smartwatch"],
    "Home & Kitchen": ["Coffee Maker", "Blender", "Air Fryer", "Vacuum"],
    "Apparel":     ["T-Shirt", "Jeans", "Sneakers", "Jacket"],
    "Sports":      ["Yoga Mat", "Dumbbells", "Bicycle", "Running Shoes"],
    "Beauty":      ["Perfume", "Skincare Set", "Hair Dryer"],
}

CHANNELS = ["Web", "Mobile App", "Marketplace", "Retail Store"]

# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------
N_CUSTOMERS = 5_000

countries, region_for_country = [], {}
for region, ctry_list in REGIONS.items():
    for c in ctry_list:
        countries.append(c)
        region_for_country[c] = region

customer_country = rng.choice(
    countries, size=N_CUSTOMERS,
    p=np.array([3, 1, 1, 2, 2, 1.5, 1, 1, 2, 1.5, 1, 1.5, 1.5, 1, 0.5]) /
      np.array([3, 1, 1, 2, 2, 1.5, 1, 1, 2, 1.5, 1, 1.5, 1.5, 1, 0.5]).sum(),
)

signup_dates = pd.to_datetime("2022-01-01") + pd.to_timedelta(
    rng.integers(0, 730, N_CUSTOMERS), unit="D"
)

customers = pd.DataFrame({
    "customer_id":   [f"C{1000 + i}" for i in range(N_CUSTOMERS)],
    "signup_date":   signup_dates,
    "country":       customer_country,
    "region":        [region_for_country[c] for c in customer_country],
    "segment":       rng.choice(
        ["Consumer", "Small Business", "Enterprise"],
        size=N_CUSTOMERS, p=[0.7, 0.2, 0.1],
    ),
})

# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------
products = []
pid = 1
for cat, items in CATEGORIES.items():
    for name in items:
        base = rng.uniform(20, 1500)
        products.append({
            "product_id":   f"P{1000 + pid}",
            "product_name": name,
            "category":     cat,
            "unit_cost":    round(base * 0.55, 2),
            "unit_price":   round(base, 2),
        })
        pid += 1
products = pd.DataFrame(products)

# ---------------------------------------------------------------------------
# Orders + order items
# ---------------------------------------------------------------------------
N_ORDERS = 40_000
order_dates = pd.to_datetime("2023-01-01") + pd.to_timedelta(
    rng.integers(0, 730, N_ORDERS), unit="D"
)

# Inject seasonality: November/December lift, summer dip
month = order_dates.month
seasonal_weight = np.where(np.isin(month, [11, 12]), 1.6,
                  np.where(np.isin(month, [6, 7, 8]), 0.85, 1.0))
order_dates = order_dates[rng.random(N_ORDERS) < seasonal_weight / seasonal_weight.max()]
N_ORDERS = len(order_dates)

cust_idx = rng.integers(0, N_CUSTOMERS, N_ORDERS)
orders = pd.DataFrame({
    "order_id":    [f"O{100000 + i}" for i in range(N_ORDERS)],
    "order_date":  order_dates,
    "customer_id": customers.loc[cust_idx, "customer_id"].values,
    "channel":     rng.choice(CHANNELS, size=N_ORDERS, p=[0.45, 0.30, 0.20, 0.05]),
    "status":      rng.choice(
        ["Completed", "Returned", "Cancelled"],
        size=N_ORDERS, p=[0.92, 0.06, 0.02],
    ),
})

# Funnel: sessions -> add_to_cart -> checkout -> purchase
# Aggregate daily funnel for the channel-level analysis
daily = orders.groupby([orders["order_date"].dt.date, "channel"]).size().reset_index(name="purchases")
daily["sessions"]      = (daily["purchases"] * rng.uniform(18, 28, len(daily))).astype(int)
daily["add_to_cart"]   = (daily["sessions"] * rng.uniform(0.18, 0.28, len(daily))).astype(int)
daily["checkout"]      = (daily["add_to_cart"] * rng.uniform(0.45, 0.65, len(daily))).astype(int)
daily.rename(columns={"order_date": "date"}, inplace=True)
daily["date"] = pd.to_datetime(daily["date"])

# ---- order_items: 1-5 lines per order -------------------------------------
n_lines_per_order = rng.integers(1, 6, N_ORDERS)
total_lines = int(n_lines_per_order.sum())

order_id_per_line = np.repeat(orders["order_id"].values, n_lines_per_order)
prod_idx          = rng.integers(0, len(products), total_lines)
quantity          = rng.integers(1, 5, total_lines)

order_items = pd.DataFrame({
    "order_item_id": np.arange(1, total_lines + 1),
    "order_id":      order_id_per_line,
    "product_id":    products.loc[prod_idx, "product_id"].values,
    "quantity":      quantity,
    "unit_price":    products.loc[prod_idx, "unit_price"].values,
    "unit_cost":     products.loc[prod_idx, "unit_cost"].values,
})
order_items["gross_revenue"] = (order_items["quantity"] * order_items["unit_price"]).round(2)
order_items["cost"]          = (order_items["quantity"] * order_items["unit_cost"]).round(2)
order_items["gross_profit"]  = (order_items["gross_revenue"] - order_items["cost"]).round(2)

# ---------------------------------------------------------------------------
# Persist
# ---------------------------------------------------------------------------
customers.to_csv(DATA_DIR / "customers.csv",     index=False)
products.to_csv(DATA_DIR  / "products.csv",      index=False)
orders.to_csv(DATA_DIR    / "orders.csv",        index=False)
order_items.to_csv(DATA_DIR / "order_items.csv", index=False)
daily.to_csv(DATA_DIR     / "daily_funnel.csv",  index=False)

print(f"Wrote {len(customers):,} customers, {len(products):,} products, "
      f"{len(orders):,} orders, {len(order_items):,} order items, "
      f"{len(daily):,} daily funnel rows to {DATA_DIR}")
