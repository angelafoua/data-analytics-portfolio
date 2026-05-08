"""
Project 2 — Customer Behavior & Retention dashboard.

Single-file interactive HTML built with Plotly. Highlights:
  * KPI cards: active customers, MRR, monthly churn, average LTV
  * Cohort retention heatmap
  * MRR + active customer trend
  * New vs returning customers
  * LTV by acquisition channel
  * RFM-lite segment breakdown

Run:
    python project_2_customer_analytics/dashboard/build_dashboard.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots

ROOT       = Path(__file__).resolve().parents[2]
DATA       = ROOT / "project_2_customer_analytics" / "data"
DASH_DIR   = ROOT / "project_2_customer_analytics" / "dashboard"
SCREENSHOT = ROOT / "assets" / "dashboard_screenshots"
SCREENSHOT.mkdir(parents=True, exist_ok=True)

pio.templates.default = "plotly_white"
PALETTE = ["#2E5BFF", "#33C2FF", "#00C48C", "#FFB822", "#F7685B", "#8C54FF"]

# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------
customers = pd.read_csv(DATA / "customers.csv",     parse_dates=["signup_date"])
tx        = pd.read_csv(DATA / "transactions.csv",  parse_dates=["transaction_date"])

tx["month"] = tx["transaction_date"].dt.to_period("M").dt.to_timestamp()
customers["cohort_month"] = customers["signup_date"].dt.to_period("M").dt.to_timestamp()
tx = tx.merge(customers[["customer_id", "cohort_month", "acq_channel", "plan"]],
              on="customer_id", how="left")

end_date = tx["transaction_date"].max()
last_month = tx["month"].max()

# ---------------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------------
mrr_last = tx.loc[tx["month"] == last_month, "amount"].sum()
active_last = tx.loc[tx["month"] == last_month, "customer_id"].nunique()

# Customer LTV (sum of transactions per customer)
ltv = tx.groupby("customer_id")["amount"].sum()
avg_ltv = ltv.mean()

# Monthly churn (mean over last 12 months)
active_per_month = (tx.groupby("month")["customer_id"]
                       .agg(set).reset_index(name="active"))
active_per_month["prev"] = active_per_month["active"].shift(1)
active_per_month = active_per_month.dropna()
active_per_month["churned"] = active_per_month.apply(
    lambda r: len(r["prev"] - r["active"]), axis=1)
active_per_month["base"]    = active_per_month["prev"].apply(len)
active_per_month["churn_pct"] = (
    active_per_month["churned"] / active_per_month["base"] * 100
)
recent_churn = active_per_month["churn_pct"].tail(12).mean()

# ---------------------------------------------------------------------------
# Cohort retention matrix
# ---------------------------------------------------------------------------
activity = (tx[["customer_id", "cohort_month", "month"]].drop_duplicates())
activity["month_index"] = (
    (activity["month"].dt.year  - activity["cohort_month"].dt.year) * 12
   + (activity["month"].dt.month - activity["cohort_month"].dt.month)
)
cohort_size = customers.groupby("cohort_month").size().rename("size")
cohort_long = (activity.groupby(["cohort_month", "month_index"])["customer_id"]
                       .nunique().reset_index(name="customers"))
cohort_long = cohort_long.merge(cohort_size, on="cohort_month")
cohort_long["retention"] = cohort_long["customers"] / cohort_long["size"] * 100

# Limit to last 18 cohorts × first 13 months for readability
recent_cohorts = sorted(cohort_long["cohort_month"].unique())[-18:]
matrix = (cohort_long[cohort_long["cohort_month"].isin(recent_cohorts)
                      & (cohort_long["month_index"] <= 12)]
          .pivot(index="cohort_month", columns="month_index", values="retention"))

# ---------------------------------------------------------------------------
# Trend frames
# ---------------------------------------------------------------------------
mrr_trend = (tx.groupby("month")
                .agg(mrr=("amount", "sum"),
                     active=("customer_id", "nunique"))
                .reset_index())

# New vs returning per month
first_tx = tx.groupby("customer_id")["transaction_date"].min().reset_index(
    name="first_date")
first_tx["first_month"] = first_tx["first_date"].dt.to_period("M").dt.to_timestamp()
tx2 = tx.merge(first_tx[["customer_id", "first_month"]], on="customer_id")
tx2["is_new"] = tx2["month"] == tx2["first_month"]
new_ret = (tx2.groupby("month")["is_new"]
              .agg(new="sum")
              .assign(active=tx2.groupby("month")["customer_id"].nunique().values)
              .reset_index())
new_ret["returning"] = new_ret["active"] - new_ret["new"]

# LTV by channel
ltv_channel = (customers.merge(ltv.rename("ltv"), on="customer_id")
                         .groupby("acq_channel")
                         .agg(avg_ltv=("ltv", "mean"),
                              customers=("customer_id", "count"))
                         .reset_index()
                         .sort_values("avg_ltv", ascending=True))

# Simple RFM-lite segments
rfm = pd.DataFrame({
    "customer_id": ltv.index,
    "monetary":    ltv.values,
})
last_tx_per_cust = tx.groupby("customer_id")["transaction_date"].max()
rfm = rfm.merge(last_tx_per_cust.rename("last_tx"), on="customer_id")
rfm["recency_days"] = (end_date - rfm["last_tx"]).dt.days
rfm["frequency"] = tx.groupby("customer_id").size().reindex(rfm["customer_id"]).values

rfm["r_score"] = pd.qcut(rfm["recency_days"],   3, labels=[1, 2, 3]).astype(int)
rfm["f_score"] = pd.qcut(rfm["frequency"].rank(method="first"), 3, labels=[3, 2, 1]).astype(int)
rfm["m_score"] = pd.qcut(rfm["monetary"].rank(method="first"),  3, labels=[3, 2, 1]).astype(int)

def segment_label(r):
    if r.r_score == 1 and r.f_score == 1 and r.m_score == 1: return "Champions"
    if r.r_score == 1 and r.f_score <= 2:                    return "Promising"
    if r.r_score == 3 and r.f_score == 1:                    return "At Risk"
    if r.r_score == 3:                                       return "Lost"
    return "Loyal"

rfm["segment"] = rfm.apply(segment_label, axis=1)
seg = rfm["segment"].value_counts().reset_index()
seg.columns = ["segment", "customers"]

# ---------------------------------------------------------------------------
# Build the figure
# ---------------------------------------------------------------------------
fig = make_subplots(
    rows=4, cols=4,
    specs=[
        [{"type": "indicator"}] * 4,
        [{"colspan": 4, "type": "xy"},  None, None, None],
        [{"colspan": 2, "type": "xy"},  None, {"colspan": 2, "type": "xy"}, None],
        [{"colspan": 2, "type": "xy"},  None, {"colspan": 2, "type": "domain"}, None],
    ],
    row_heights=[0.13, 0.32, 0.27, 0.28],
    vertical_spacing=0.08,
    horizontal_spacing=0.08,
    subplot_titles=(
        "", "", "", "",
        "Cohort retention — last 18 signup months × months since signup",
        "New vs returning paying customers",
        "Average LTV by acquisition channel",
        "MRR & active customers",
        "Customer segments (RFM-lite)",
    ),
)

def kpi(value, title, prefix="", suffix="", color=PALETTE[0]):
    return go.Indicator(
        mode="number",
        value=value,
        number={"prefix": prefix, "suffix": suffix, "valueformat": ",.0f",
                "font": {"size": 36, "color": color}},
        title={"text": f"<span style='font-size:14px;color:#555'>{title}</span>"},
    )

fig.add_trace(kpi(active_last, "Active customers (last month)",       color=PALETTE[0]), row=1, col=1)
fig.add_trace(kpi(mrr_last,    "MRR (last month)", prefix="$",        color=PALETTE[2]), row=1, col=2)
fig.add_trace(kpi(recent_churn,"Avg. monthly churn (12mo)", suffix="%", color=PALETTE[4]), row=1, col=3)
fig.add_trace(kpi(avg_ltv,     "Average LTV", prefix="$",             color=PALETTE[3]), row=1, col=4)

# ---- Cohort heatmap ------------------------------------------------------
heat_z = matrix.values
heat_text = np.where(np.isnan(heat_z), "", np.round(heat_z, 0).astype(str))
fig.add_trace(
    go.Heatmap(
        z=heat_z,
        x=[f"M{c}" for c in matrix.columns],
        y=[m.strftime("%b %Y") for m in matrix.index],
        colorscale=[[0, "#FFFFFF"], [0.5, "#33C2FF"], [1, "#2E5BFF"]],
        zmin=0, zmax=100,
        text=heat_text, texttemplate="%{text}",
        hovertemplate="Cohort: %{y}<br>Month %{x}<br>"
                       "Retention: %{z:.1f}%<extra></extra>",
        colorbar=dict(title="Retention %", thickness=12, x=1.02),
    ),
    row=2, col=1,
)

# ---- New vs returning ----------------------------------------------------
fig.add_trace(
    go.Bar(x=new_ret["month"], y=new_ret["new"], name="New",
           marker_color=PALETTE[2]),
    row=3, col=1,
)
fig.add_trace(
    go.Bar(x=new_ret["month"], y=new_ret["returning"], name="Returning",
           marker_color=PALETTE[0]),
    row=3, col=1,
)

# ---- LTV by channel ------------------------------------------------------
fig.add_trace(
    go.Bar(y=ltv_channel["acq_channel"], x=ltv_channel["avg_ltv"],
           orientation="h", marker_color=PALETTE[5],
           text=[f"${v:,.0f}" for v in ltv_channel["avg_ltv"]],
           textposition="outside",
           hovertemplate="%{y}<br>Avg LTV: $%{x:,.0f}<br>"
                          "Customers: %{customdata:,}<extra></extra>",
           customdata=ltv_channel["customers"],
           showlegend=False),
    row=3, col=3,
)

# ---- MRR + active --------------------------------------------------------
fig.add_trace(
    go.Bar(x=mrr_trend["month"], y=mrr_trend["mrr"],
           name="MRR", marker_color=PALETTE[0],
           hovertemplate="%{x|%b %Y}<br>MRR: $%{y:,.0f}<extra></extra>"),
    row=4, col=1,
)
fig.add_trace(
    go.Scatter(x=mrr_trend["month"], y=mrr_trend["active"],
               name="Active customers", mode="lines+markers",
               yaxis="y6", line=dict(color=PALETTE[3], width=3),
               hovertemplate="%{x|%b %Y}<br>Active: %{y:,}<extra></extra>"),
    row=4, col=1,
)

# ---- Segment pie ---------------------------------------------------------
fig.add_trace(
    go.Pie(labels=seg["segment"], values=seg["customers"],
           marker={"colors": PALETTE},
           textinfo="label+percent",
           hole=0.45),
    row=4, col=3,
)

# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------
fig.update_layout(
    title={"text": "<b>Customer Behavior & Retention Dashboard</b><br>"
                    "<span style='font-size:13px;color:#666'>"
                    "Subscription business · Jan 2022 – Dec 2024</span>",
           "x": 0.01, "xanchor": "left"},
    height=1500, width=1500,
    barmode="stack",
    margin=dict(l=60, r=80, t=110, b=40),
    legend=dict(orientation="h", yanchor="bottom", y=1.02,
                xanchor="right", x=1, bgcolor="rgba(0,0,0,0)"),
)
fig.update_yaxes(title_text="Customers", row=3, col=1)
fig.update_xaxes(title_text="USD",       row=3, col=3)
fig.update_yaxes(title_text="MRR (USD)", row=4, col=1)

# ---------------------------------------------------------------------------
# Persist
# ---------------------------------------------------------------------------
out = DASH_DIR / "customer_dashboard.html"
fig.write_html(out, include_plotlyjs="cdn", full_html=True)
print(f"Wrote interactive dashboard to {out}")

try:
    fig.write_image(SCREENSHOT / "project_2_customer_dashboard.png",
                    width=1500, height=1500, scale=2)
    print("Wrote screenshot")
except Exception as e:
    print(f"Screenshot skipped: {e}")
