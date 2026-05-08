"""
Generate a SaaS-style customer transactions dataset for Project 2.

Models a subscription / repeat-purchase business where retention,
cohort behaviour, churn, and LTV are the core questions.

Outputs:
    - customers.csv      (signup cohort, segment, acquisition channel)
    - transactions.csv   (one row per paid event, with revenue)

Run from repo root:
    python project_2_customer_analytics/scripts/generate_data.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

SEED = 7
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

rng = np.random.default_rng(SEED)

# ---------------------------------------------------------------------------
# Customers / signup cohorts
# ---------------------------------------------------------------------------
N_CUSTOMERS = 8_000
START = pd.Timestamp("2022-01-01")
END   = pd.Timestamp("2024-12-31")

signup_dates = START + pd.to_timedelta(
    rng.integers(0, (END - START).days, N_CUSTOMERS), unit="D"
)
# Bias signups upward through time to simulate growth
weight = (signup_dates - START).days / (END - START).days
keep = rng.random(N_CUSTOMERS) < (0.4 + 0.6 * weight)
signup_dates = signup_dates[keep]
N_CUSTOMERS = len(signup_dates)

countries = rng.choice(
    ["US", "UK", "DE", "FR", "BR", "JP", "AU", "CA", "IN", "ES"],
    size=N_CUSTOMERS,
    p=[0.30, 0.10, 0.08, 0.08, 0.07, 0.07, 0.06, 0.10, 0.08, 0.06],
)
acq_channel = rng.choice(
    ["Organic", "Paid Search", "Paid Social", "Referral", "Email", "Affiliate"],
    size=N_CUSTOMERS,
    p=[0.30, 0.25, 0.18, 0.10, 0.10, 0.07],
)
plan = rng.choice(
    ["Starter", "Pro", "Business", "Enterprise"],
    size=N_CUSTOMERS,
    p=[0.50, 0.30, 0.15, 0.05],
)
plan_price = {"Starter": 19, "Pro": 49, "Business": 199, "Enterprise": 599}
monthly_price = np.array([plan_price[p] for p in plan], dtype=float)

customers = pd.DataFrame({
    "customer_id":   [f"U{10000 + i}" for i in range(N_CUSTOMERS)],
    "signup_date":   signup_dates,
    "country":       countries,
    "acq_channel":   acq_channel,
    "plan":          plan,
    "monthly_price": monthly_price,
})
customers = customers.sort_values("signup_date").reset_index(drop=True)

# ---------------------------------------------------------------------------
# Retention / churn simulation
# ---------------------------------------------------------------------------
# Each plan has its own monthly churn hazard; channels modulate it slightly.
plan_churn = {"Starter": 0.10, "Pro": 0.06, "Business": 0.04, "Enterprise": 0.025}
channel_mult = {
    "Organic": 0.9, "Paid Search": 1.05, "Paid Social": 1.20,
    "Referral": 0.7, "Email": 1.0, "Affiliate": 1.10,
}

def lifetime_months(plan_, channel_):
    base = plan_churn[plan_] * channel_mult[channel_]
    # Geometric distribution (memoryless monthly churn)
    return int(rng.geometric(base))

lifetimes = np.array(
    [lifetime_months(p, c) for p, c in zip(customers["plan"], customers["acq_channel"])]
)
# Cap so a customer can't churn after the data window
months_available = (
    (END.to_period("M") - customers["signup_date"].dt.to_period("M")).apply(lambda x: x.n)
).to_numpy()
lifetimes = np.minimum(lifetimes, months_available + 1)

# ---------------------------------------------------------------------------
# Build the transactions table
# ---------------------------------------------------------------------------
records = []
for cid, signup, plan_, price, life in zip(
    customers["customer_id"], customers["signup_date"], customers["plan"],
    customers["monthly_price"], lifetimes,
):
    for m in range(life):
        ts = (signup + pd.DateOffset(months=m)).normalize()
        if ts > END:
            break
        # 8% of charges in any month also include an upsell add-on
        addon = rng.uniform(20, 120) if rng.random() < 0.08 else 0.0
        records.append((cid, ts, plan_, round(price + addon, 2),
                        "subscription" if addon == 0 else "subscription+addon"))

transactions = pd.DataFrame(
    records, columns=["customer_id", "transaction_date", "plan", "amount", "type"]
)
transactions["transaction_id"] = np.arange(1, len(transactions) + 1)
transactions = transactions[
    ["transaction_id", "customer_id", "transaction_date", "plan", "amount", "type"]
]

# ---------------------------------------------------------------------------
# Persist
# ---------------------------------------------------------------------------
customers.to_csv(DATA_DIR / "customers.csv",     index=False)
transactions.to_csv(DATA_DIR / "transactions.csv", index=False)

print(f"Wrote {len(customers):,} customers, {len(transactions):,} transactions to {DATA_DIR}")
print(f"Date range: {transactions['transaction_date'].min().date()} → "
      f"{transactions['transaction_date'].max().date()}")
