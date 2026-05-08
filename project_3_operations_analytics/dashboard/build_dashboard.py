"""
Project 3 — Operations & Data Quality dashboard.

KPI cards on top, SLA + cost charts in the middle, data-quality scorecard
on the bottom. Single self-contained HTML.

Run:
    python project_3_operations_analytics/dashboard/build_dashboard.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots

ROOT       = Path(__file__).resolve().parents[2]
DATA       = ROOT / "project_3_operations_analytics" / "data"
DASH_DIR   = ROOT / "project_3_operations_analytics" / "dashboard"
SCREENSHOT = ROOT / "assets" / "dashboard_screenshots"
SCREENSHOT.mkdir(parents=True, exist_ok=True)

pio.templates.default = "plotly_white"
PALETTE  = ["#2E5BFF", "#33C2FF", "#00C48C", "#FFB822", "#F7685B", "#8C54FF"]
TRAFFIC  = {"On-time": "#00C48C", "Late": "#FFB822", "Failed": "#F7685B"}
SLA_DAYS = 5

# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------
clean = pd.read_csv(DATA / "shipments.csv",
                    parse_dates=["order_date", "ship_date", "delivery_date"])
raw   = pd.read_csv(DATA / "shipments_raw.csv",
                    parse_dates=["order_date", "ship_date", "delivery_date"])

# ---------------------------------------------------------------------------
# Operations KPIs
# ---------------------------------------------------------------------------
on_time_pct = (clean["status"] == "On-time").mean() * 100
late_pct    = (clean["status"] == "Late").mean() * 100
failed_pct  = (clean["status"] == "Failed").mean() * 100
avg_lead    = clean["total_days"].mean()
avg_cost    = clean["shipping_cost"].mean()

# ---------------------------------------------------------------------------
# Data-quality KPIs
# ---------------------------------------------------------------------------
n = len(raw)
n_null_order_date = raw["order_date"].isna().sum()
n_null_wh_city    = raw["warehouse_city"].isna().sum()
n_null_delivery   = raw["delivery_date"].isna().sum()
n_neg_cost        = (raw["shipping_cost"] < 0).sum()
n_bad_date        = (raw["delivery_date"] < raw["order_date"]).sum()
n_unknown_car     = (~raw["carrier"].isin(["DHL", "FedEx", "UPS", "USPS", "Local"])).sum()
n_dups            = raw.duplicated(subset=["shipment_id"]).sum()
total_issues      = (n_null_order_date + n_null_wh_city + n_bad_date
                     + n_neg_cost + n_unknown_car + n_dups)
dq_score          = 100 - (total_issues / n * 100)

# ---------------------------------------------------------------------------
# Aggregates for charts
# ---------------------------------------------------------------------------
wh = (clean.groupby(["warehouse_id", "warehouse_city"])
            .agg(shipments=("shipment_id", "count"),
                 on_time_pct=("status", lambda s: (s == "On-time").mean() * 100),
                 avg_processing=("processing_days", "mean"),
                 avg_transit=("transit_days", "mean"))
            .reset_index()
            .sort_values("on_time_pct"))

car = (clean.groupby("carrier")
              .agg(shipments=("shipment_id", "count"),
                   on_time_pct=("status", lambda s: (s == "On-time").mean() * 100),
                   failed_pct =("status", lambda s: (s == "Failed").mean() * 100),
                   avg_transit=("transit_days", "mean"),
                   avg_cost   =("shipping_cost", "mean"))
              .reset_index()
              .sort_values("on_time_pct", ascending=False))

# Daily on-time % (with 30-day rolling)
daily = (clean.groupby("ship_date")
                .agg(total=("shipment_id", "count"),
                     on_time=("status", lambda s: (s == "On-time").sum()))
                .reset_index())
daily["on_time_pct"]    = daily["on_time"] / daily["total"] * 100
daily["rolling_30_pct"] = (daily["on_time"].rolling(30, min_periods=5).sum()
                           / daily["total"].rolling(30, min_periods=5).sum()) * 100

# Status mix by product line
mix = (clean.groupby(["product_line", "status"])
              .size().unstack(fill_value=0))
for col in ("On-time", "Late", "Failed"):
    if col not in mix.columns:
        mix[col] = 0
mix_pct = mix.div(mix.sum(axis=1), axis=0) * 100

# DQ rule breakdown
dq_rules = pd.DataFrame({
    "rule":   ["Missing order_date", "Missing warehouse_city",
               "Missing delivery_date", "Negative shipping cost",
               "Delivery before order date", "Unknown carrier code",
               "Duplicate shipment_id"],
    "count":  [n_null_order_date, n_null_wh_city, n_null_delivery,
               n_neg_cost, n_bad_date, n_unknown_car, n_dups],
})
dq_rules["pct_of_rows"] = dq_rules["count"] / n * 100
dq_rules = dq_rules.sort_values("count", ascending=True)

# ---------------------------------------------------------------------------
# Build the figure
# ---------------------------------------------------------------------------
fig = make_subplots(
    rows=4, cols=4,
    specs=[
        [{"type": "indicator"}] * 4,
        [{"colspan": 4, "type": "xy"}, None, None, None],
        [{"colspan": 2, "type": "xy"}, None, {"colspan": 2, "type": "xy"}, None],
        [{"colspan": 2, "type": "xy"}, None, {"colspan": 2, "type": "indicator"}, None],
    ],
    row_heights=[0.13, 0.27, 0.30, 0.30],
    vertical_spacing=0.09,
    horizontal_spacing=0.08,
    subplot_titles=(
        "", "", "", "",
        "Daily on-time % &nbsp;(target = 90%)",
        "Warehouse SLA — sorted worst → best",
        "Carrier scorecard",
        "Data-quality issues by rule",
        "",
    ),
)

def kpi(value, title, prefix="", suffix="", color=PALETTE[0], decimals=1):
    fmt = f",.{decimals}f"
    return go.Indicator(
        mode="number",
        value=value,
        number={"prefix": prefix, "suffix": suffix, "valueformat": fmt,
                "font": {"size": 36, "color": color}},
        title={"text": f"<span style='font-size:14px;color:#555'>{title}</span>"},
    )

fig.add_trace(kpi(on_time_pct, "On-time delivery", suffix="%", color=PALETTE[2]), row=1, col=1)
fig.add_trace(kpi(avg_lead, "Avg lead time", suffix=" d", color=PALETTE[0]), row=1, col=2)
fig.add_trace(kpi(failed_pct, "Failed delivery", suffix="%", color=PALETTE[4]), row=1, col=3)
fig.add_trace(kpi(avg_cost, "Avg shipping cost", prefix="$", color=PALETTE[3], decimals=2),
              row=1, col=4)

# ---- Daily on-time trend (rolling) -----------------------------------------
fig.add_trace(
    go.Scatter(x=daily["ship_date"], y=daily["on_time_pct"],
               mode="markers", name="Daily",
               marker=dict(color=PALETTE[1], size=4, opacity=0.5),
               hovertemplate="%{x|%Y-%m-%d}<br>"
                              "Daily on-time: %{y:.1f}%<extra></extra>"),
    row=2, col=1,
)
fig.add_trace(
    go.Scatter(x=daily["ship_date"], y=daily["rolling_30_pct"],
               mode="lines", name="30-day rolling",
               line=dict(color=PALETTE[0], width=3),
               hovertemplate="%{x|%Y-%m-%d}<br>"
                              "30-day rolling: %{y:.1f}%<extra></extra>"),
    row=2, col=1,
)
fig.add_trace(
    go.Scatter(x=[daily["ship_date"].min(), daily["ship_date"].max()],
               y=[90, 90], mode="lines", name="Target 90%",
               line=dict(color="#F7685B", width=1.5, dash="dash"),
               hoverinfo="skip", showlegend=True),
    row=2, col=1,
)

# ---- Warehouse SLA --------------------------------------------------------
fig.add_trace(
    go.Bar(y=wh["warehouse_city"], x=wh["on_time_pct"],
           orientation="h",
           marker_color=[PALETTE[4] if v < 80 else
                         PALETTE[3] if v < 90 else PALETTE[2]
                         for v in wh["on_time_pct"]],
           text=[f"{v:.1f}%" for v in wh["on_time_pct"]],
           textposition="outside",
           hovertemplate="%{y}<br>On-time: %{x:.1f}%<br>"
                          "Avg processing: %{customdata[0]:.2f} d<br>"
                          "Avg transit: %{customdata[1]:.2f} d<extra></extra>",
           customdata=wh[["avg_processing", "avg_transit"]].values,
           showlegend=False),
    row=3, col=1,
)

# ---- Carrier scorecard ----------------------------------------------------
fig.add_trace(
    go.Bar(x=car["carrier"], y=car["on_time_pct"],
           name="On-time %", marker_color=PALETTE[2],
           text=[f"{v:.1f}%" for v in car["on_time_pct"]],
           textposition="outside",
           hovertemplate="%{x}<br>On-time: %{y:.1f}%<br>"
                          "Failed: %{customdata[0]:.2f}%<br>"
                          "Avg cost: $%{customdata[1]:.2f}<extra></extra>",
           customdata=car[["failed_pct", "avg_cost"]].values,
           showlegend=False),
    row=3, col=3,
)

# ---- DQ rules -------------------------------------------------------------
fig.add_trace(
    go.Bar(y=dq_rules["rule"], x=dq_rules["count"],
           orientation="h",
           marker_color=PALETTE[4],
           text=[f"{c:,} ({p:.2f}%)" for c, p in
                 zip(dq_rules["count"], dq_rules["pct_of_rows"])],
           textposition="outside",
           hovertemplate="%{y}<br>Rows: %{x:,}<extra></extra>",
           showlegend=False),
    row=4, col=1,
)

# ---- DQ score gauge -------------------------------------------------------
fig.add_trace(
    go.Indicator(
        mode="gauge+number",
        value=dq_score,
        number={"suffix": "%", "valueformat": ".2f",
                "font": {"size": 40, "color": PALETTE[2] if dq_score >= 95 else PALETTE[4]}},
        title={"text": "<b>Data-quality score</b><br>"
                        "<span style='font-size:11px;color:#888'>"
                        "100% − rule-failure rate</span>"},
        gauge={
            "axis": {"range": [80, 100], "ticksuffix": "%"},
            "bar":  {"color": PALETTE[2]},
            "steps": [
                {"range": [80, 90], "color": "#FFE3E0"},
                {"range": [90, 95], "color": "#FFF3D6"},
                {"range": [95, 100], "color": "#E0F7EC"},
            ],
            "threshold": {"line": {"color": "red", "width": 3},
                          "thickness": 0.75, "value": 95},
        },
    ),
    row=4, col=3,
)

# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------
fig.update_layout(
    title={"text": "<b>Operations & Data-Quality Dashboard</b><br>"
                    "<span style='font-size:13px;color:#666'>"
                    "FY 2024 fulfillment · 6 warehouses · 5 carriers</span>",
           "x": 0.01, "xanchor": "left"},
    height=1500, width=1500,
    margin=dict(l=60, r=40, t=110, b=40),
    legend=dict(orientation="h", yanchor="bottom", y=1.02,
                xanchor="right", x=1, bgcolor="rgba(0,0,0,0)"),
)
fig.update_yaxes(title_text="On-time %", row=2, col=1)
fig.update_yaxes(range=[60, 100], row=2, col=1)
fig.update_xaxes(title_text="On-time %", row=3, col=1)
fig.update_yaxes(title_text="On-time %", row=3, col=3)
fig.update_xaxes(title_text="Rows", row=4, col=1)

# ---------------------------------------------------------------------------
# Persist
# ---------------------------------------------------------------------------
out = DASH_DIR / "operations_dashboard.html"
fig.write_html(out, include_plotlyjs="cdn", full_html=True)
print(f"Wrote interactive dashboard to {out}")

try:
    fig.write_image(SCREENSHOT / "project_3_operations_dashboard.png",
                    width=1500, height=1500, scale=2)
    print("Wrote screenshot")
except Exception as e:
    print(f"Screenshot skipped: {e}")
