"""
Generate a logistics / fulfillment dataset for Project 3.

Models a multi-warehouse, multi-carrier fulfillment operation with
realistic data-quality issues injected: missing values, duplicates,
out-of-range dates, late-arriving records.

Outputs:
    - shipments_raw.csv  (intentionally messy — for cleaning + DQ checks)
    - shipments.csv      (clean version that the operations dashboard uses)

Run from repo root:
    python project_3_operations_analytics/scripts/generate_data.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

SEED = 13
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(SEED)

# ---------------------------------------------------------------------------
# Reference dimensions
# ---------------------------------------------------------------------------
WAREHOUSES = {
    "WH-AMS": ("Amsterdam",   "Europe",        2),  # processing SLA in days
    "WH-LON": ("London",      "Europe",        2),
    "WH-NYC": ("New York",    "North America", 1),
    "WH-LAX": ("Los Angeles", "North America", 1),
    "WH-SIN": ("Singapore",   "APAC",          2),
    "WH-SAO": ("Sao Paulo",   "LATAM",         3),
}

CARRIERS = {
    "DHL":   {"speed": 0.9, "fail_rate": 0.015},
    "FedEx": {"speed": 0.95, "fail_rate": 0.020},
    "UPS":   {"speed": 1.00, "fail_rate": 0.020},
    "USPS":  {"speed": 1.15, "fail_rate": 0.035},
    "Local": {"speed": 1.30, "fail_rate": 0.055},
}

PRODUCT_LINES = ["Apparel", "Electronics", "Home", "Beauty", "Sports"]

PROMISED_SLA_DAYS = 7  # Customer-facing delivery promise (calendar days)

# ---------------------------------------------------------------------------
# Generate
# ---------------------------------------------------------------------------
N = 30_000
order_dates = pd.to_datetime("2024-01-01") + pd.to_timedelta(
    rng.integers(0, 365, N), unit="D"
)

wh_ids = list(WAREHOUSES.keys())
warehouse = rng.choice(wh_ids, size=N, p=[0.18, 0.15, 0.20, 0.18, 0.17, 0.12])
carrier = rng.choice(list(CARRIERS.keys()), size=N, p=[0.30, 0.20, 0.20, 0.20, 0.10])
line = rng.choice(PRODUCT_LINES, size=N)

processing_days = np.array(
    [WAREHOUSES[w][2] + max(0, rng.normal(0, 0.4)) for w in warehouse]
).round(2)
# Late picks ~6% of the time add a 1-3 day delay
pick_late = rng.random(N) < 0.06
processing_days = processing_days + np.where(pick_late, rng.uniform(1, 3, N), 0)

# Transit days driven by carrier speed + warehouse-region noise
base_transit = np.array([2.5 if WAREHOUSES[w][1] in ("Europe", "North America") else 4.0
                         for w in warehouse])
transit_days = base_transit * np.array([CARRIERS[c]["speed"] for c in carrier])
transit_days = transit_days + rng.normal(0, 0.6, N)
transit_days = np.clip(transit_days, 1, None)

# Failed deliveries
failed = rng.random(N) < np.array([CARRIERS[c]["fail_rate"] for c in carrier])

ship_dates    = order_dates + pd.to_timedelta(processing_days, unit="D")
delivery_dates = ship_dates + pd.to_timedelta(transit_days, unit="D")

total_days = ((delivery_dates - order_dates) / pd.Timedelta(days=1)).to_numpy()
sla_breach = total_days > PROMISED_SLA_DAYS

# Cost per shipment varies by carrier + warehouse region
unit_cost = np.array([8 if WAREHOUSES[w][1] in ("Europe", "North America") else 14
                      for w in warehouse]) \
            + np.array([0 if c == "Local" else 4 for c in carrier]) \
            + rng.normal(0, 1.5, N)

shipments = pd.DataFrame({
    "shipment_id":    [f"S{200000 + i}" for i in range(N)],
    "order_id":       [f"O{500000 + i}" for i in range(N)],
    "order_date":     order_dates,
    "ship_date":      ship_dates,
    "delivery_date":  pd.Series(delivery_dates).where(~failed, pd.NaT),
    "warehouse_id":   warehouse,
    "warehouse_city": [WAREHOUSES[w][0] for w in warehouse],
    "region":         [WAREHOUSES[w][1] for w in warehouse],
    "carrier":        carrier,
    "product_line":   line,
    "processing_days": processing_days.round(2),
    "transit_days":   transit_days.round(2),
    "total_days":     total_days.round(2),
    "shipping_cost":  unit_cost.round(2),
    "status":         np.where(failed, "Failed",
                       np.where(sla_breach, "Late", "On-time")),
})
shipments = shipments.sort_values("order_date").reset_index(drop=True)

# ---------------------------------------------------------------------------
# Build a *raw* messy version for the data-quality story
# ---------------------------------------------------------------------------
raw = shipments.copy()

# 1. Drop ~3% of warehouse_city values (missing dimension)
mask = rng.random(len(raw)) < 0.03
raw.loc[mask, "warehouse_city"] = np.nan

# 2. Null out 1.5% of order_dates (missing critical field)
mask = rng.random(len(raw)) < 0.015
raw.loc[mask, "order_date"] = pd.NaT

# 3. Inject ~0.5% duplicate rows (same shipment_id reappears)
dup_idx = rng.choice(raw.index, size=int(0.005 * len(raw)), replace=False)
raw = pd.concat([raw, raw.loc[dup_idx]], ignore_index=True)

# 4. ~0.4% out-of-range delivery dates (clearly wrong: before order_date)
mask = rng.random(len(raw)) < 0.004
raw.loc[mask, "delivery_date"] = raw.loc[mask, "order_date"] - pd.Timedelta(days=2)

# 5. ~2% have negative shipping_cost (bad ETL upstream)
mask = rng.random(len(raw)) < 0.02
raw.loc[mask, "shipping_cost"] = -raw.loc[mask, "shipping_cost"]

# 6. 1% have an unknown carrier code (FK violation upstream)
mask = rng.random(len(raw)) < 0.01
raw.loc[mask, "carrier"] = "UNKNOWN"

# ---------------------------------------------------------------------------
# Persist
# ---------------------------------------------------------------------------
raw.to_csv(DATA_DIR / "shipments_raw.csv", index=False)
shipments.to_csv(DATA_DIR / "shipments.csv", index=False)

print(f"Wrote {len(shipments):,} clean shipments and "
      f"{len(raw):,} raw (messy) rows to {DATA_DIR}")
