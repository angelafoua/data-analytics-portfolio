"""
Build a single-file HTML dashboard for the Sales Performance project.

The dashboard is a self-contained interactive HTML file that mirrors what
an executive Power BI / Tableau page would look like — KPI cards on top,
trends + breakdowns below.

Run:
    python project_1_sales_analysis/dashboard/build_dashboard.py
Outputs:
    project_1_sales_analysis/dashboard/sales_dashboard.html
    assets/dashboard_screenshots/project_1_*.png  (static images for README)
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots

ROOT       = Path(__file__).resolve().parents[2]
DATA       = ROOT / "project_1_sales_analysis" / "data"
DASH_DIR   = ROOT / "project_1_sales_analysis" / "dashboard"
SCREENSHOT = ROOT / "assets" / "dashboard_screenshots"
SCREENSHOT.mkdir(parents=True, exist_ok=True)

pio.templates.default = "plotly_white"
PALETTE = ["#2E5BFF", "#33C2FF", "#00C48C", "#FFB822", "#F7685B", "#8C54FF"]

# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------
customers   = pd.read_csv(DATA / "customers.csv",   parse_dates=["signup_date"])
products    = pd.read_csv(DATA / "products.csv")
orders      = pd.read_csv(DATA / "orders.csv",      parse_dates=["order_date"])
order_items = pd.read_csv(DATA / "order_items.csv")
funnel      = pd.read_csv(DATA / "daily_funnel.csv", parse_dates=["date"])

active = orders[orders["status"] != "Cancelled"]
items  = order_items.merge(active[["order_id", "order_date", "customer_id", "channel"]],
                           on="order_id")
items  = items.merge(products[["product_id", "category", "product_name"]], on="product_id")
items  = items.merge(customers[["customer_id", "region", "country", "segment"]],
                     on="customer_id")

# ---------------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------------
total_revenue = items["gross_revenue"].sum()
total_profit  = items["gross_profit"].sum()
margin_pct    = total_profit / total_revenue * 100
order_value   = items.groupby("order_id")["gross_revenue"].sum()
aov           = order_value.mean()
return_rate   = (orders["status"] == "Returned").mean() * 100

# ---------------------------------------------------------------------------
# Aggregations for charts
# ---------------------------------------------------------------------------
monthly = (items
           .assign(month=items["order_date"].dt.to_period("M").dt.to_timestamp())
           .groupby("month")
           .agg(revenue=("gross_revenue", "sum"),
                profit =("gross_profit",  "sum"))
           .reset_index())
monthly["mom_pct"] = monthly["revenue"].pct_change() * 100

cat_perf = (items.groupby("category")
                  .agg(revenue=("gross_revenue", "sum"),
                       profit =("gross_profit",  "sum"),
                       units  =("quantity",      "sum"))
                  .reset_index()
                  .sort_values("revenue", ascending=True))
cat_perf["margin_pct"] = cat_perf["profit"] / cat_perf["revenue"] * 100

region_perf = (items.groupby("region")
                     .agg(revenue=("gross_revenue", "sum"),
                          customers=("customer_id", "nunique"))
                     .reset_index()
                     .sort_values("revenue", ascending=False))

top_products = (items.groupby(["product_name", "category"])
                      .agg(revenue=("gross_revenue", "sum"),
                           units  =("quantity",      "sum"))
                      .reset_index()
                      .sort_values("revenue", ascending=False)
                      .head(10))

top_customers = (items.groupby(["customer_id", "country", "segment"])
                       .agg(revenue=("gross_revenue", "sum"),
                            orders =("order_id", "nunique"))
                       .reset_index()
                       .sort_values("revenue", ascending=False)
                       .head(10))

channel_funnel = (funnel.groupby("channel")
                         [["sessions", "add_to_cart", "checkout", "purchases"]]
                         .sum().reset_index())

# ---------------------------------------------------------------------------
# Build the figure
# ---------------------------------------------------------------------------
fig = make_subplots(
    rows=4, cols=4,
    specs=[
        [{"type": "indicator"}] * 4,
        [{"colspan": 4, "type": "xy"},  None, None, None],
        [{"colspan": 2, "type": "xy"},  None, {"colspan": 2, "type": "xy"}, None],
        [{"colspan": 2, "type": "xy"},  None, {"colspan": 2, "type": "xy"}, None],
    ],
    row_heights=[0.13, 0.27, 0.30, 0.30],
    vertical_spacing=0.08,
    horizontal_spacing=0.08,
    subplot_titles=(
        "", "", "", "",
        "Monthly revenue & gross profit",
        "Revenue by category",
        "Top 10 products by revenue",
        "Revenue share by region",
        "Channel funnel — overall conversion",
    ),
)

# --- KPI cards -------------------------------------------------------------
def kpi_card(value, title, prefix="", suffix="", color=PALETTE[0]):
    return go.Indicator(
        mode="number",
        value=value,
        number={"prefix": prefix, "suffix": suffix, "valueformat": ",.0f",
                "font": {"size": 38, "color": color}},
        title={"text": f"<span style='font-size:14px;color:#555'>{title}</span>"},
    )

fig.add_trace(kpi_card(total_revenue, "Net Revenue",     prefix="$"),                row=1, col=1)
fig.add_trace(kpi_card(margin_pct,    "Gross Margin",    suffix="%", color=PALETTE[2]), row=1, col=2)
fig.add_trace(kpi_card(aov,           "Avg. Order Value", prefix="$", color=PALETTE[3]), row=1, col=3)
fig.add_trace(kpi_card(return_rate,   "Return Rate",     suffix="%", color=PALETTE[4]), row=1, col=4)

# --- Monthly revenue trend -------------------------------------------------
fig.add_trace(
    go.Bar(x=monthly["month"], y=monthly["revenue"],
           name="Revenue", marker_color=PALETTE[0],
           hovertemplate="%{x|%b %Y}<br>Revenue: $%{y:,.0f}<extra></extra>"),
    row=2, col=1,
)
fig.add_trace(
    go.Scatter(x=monthly["month"], y=monthly["profit"],
               mode="lines+markers", name="Gross profit",
               line=dict(color=PALETTE[2], width=3),
               hovertemplate="%{x|%b %Y}<br>Gross profit: $%{y:,.0f}<extra></extra>"),
    row=2, col=1,
)

# --- Category performance --------------------------------------------------
fig.add_trace(
    go.Bar(y=cat_perf["category"], x=cat_perf["revenue"],
           orientation="h", marker_color=PALETTE[1],
           name="Category revenue",
           text=[f"${v/1e6:.1f}M" for v in cat_perf["revenue"]],
           textposition="outside",
           hovertemplate="%{y}<br>Revenue: $%{x:,.0f}<extra></extra>",
           showlegend=False),
    row=3, col=1,
)

# --- Top products ----------------------------------------------------------
fig.add_trace(
    go.Bar(y=top_products["product_name"][::-1],
           x=top_products["revenue"][::-1],
           orientation="h", marker_color=PALETTE[5],
           name="Top products",
           text=[f"${v/1e6:.2f}M" for v in top_products["revenue"][::-1]],
           textposition="outside",
           hovertemplate="%{y}<br>Revenue: $%{x:,.0f}<extra></extra>",
           showlegend=False),
    row=3, col=3,
)

# --- Region share ----------------------------------------------------------
fig.add_trace(
    go.Bar(x=region_perf["region"], y=region_perf["revenue"],
           marker_color=PALETTE[3], name="Region revenue",
           text=[f"${v/1e6:.1f}M" for v in region_perf["revenue"]],
           textposition="outside",
           hovertemplate="%{x}<br>Revenue: $%{y:,.0f}<br>"
                          "Customers: %{customdata:,}<extra></extra>",
           customdata=region_perf["customers"],
           showlegend=False),
    row=4, col=1,
)

# --- Channel funnel --------------------------------------------------------
stages = ["sessions", "add_to_cart", "checkout", "purchases"]
stage_labels = ["Sessions", "Add to Cart", "Checkout", "Purchase"]
for i, ch in enumerate(channel_funnel["channel"]):
    row = channel_funnel[channel_funnel["channel"] == ch].iloc[0]
    fig.add_trace(
        go.Funnel(
            name=ch,
            y=stage_labels,
            x=[row[s] for s in stages],
            marker={"color": PALETTE[i % len(PALETTE)]},
            textinfo="value+percent initial",
        ),
        row=4, col=3,
    )

# ---------------------------------------------------------------------------
# Layout polish
# ---------------------------------------------------------------------------
fig.update_layout(
    title={
        "text": "<b>Sales Performance Dashboard</b><br>"
                "<span style='font-size:13px;color:#666'>"
                "FY 2023 – 2024 · all channels · all regions</span>",
        "x": 0.01, "xanchor": "left",
    },
    height=1450, width=1500,
    barmode="group",
    margin=dict(l=60, r=40, t=110, b=40),
    legend=dict(orientation="h", yanchor="bottom", y=1.02,
                xanchor="right", x=1, bgcolor="rgba(0,0,0,0)"),
)
fig.update_yaxes(title_text="USD", row=2, col=1)
fig.update_xaxes(title_text="USD", row=3, col=1)
fig.update_xaxes(title_text="USD", row=3, col=3)
fig.update_yaxes(title_text="USD", row=4, col=1)

# ---------------------------------------------------------------------------
# Persist
# ---------------------------------------------------------------------------
out_html = DASH_DIR / "sales_dashboard.html"
fig.write_html(out_html, include_plotlyjs="cdn", full_html=True)
print(f"Wrote interactive dashboard to {out_html}")

# Also save individual charts as PNG fallbacks so the README always renders.
try:
    import plotly.io as pio  # noqa: F401  (kaleido must be present)
    fig.write_image(SCREENSHOT / "project_1_sales_dashboard.png",
                    width=1500, height=1450, scale=2)
    print("Wrote screenshot")
except Exception as e:  # kaleido not installed in every environment
    print(f"Screenshot skipped (no kaleido): {e}")
