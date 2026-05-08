# Project 3 — Operations Efficiency & Data Quality

> **Audience:** COO, Head of Logistics, Head of Data.
> **Period covered:** FY 2024 (12 months).
> **Data:** 30,000 shipments across 6 warehouses and 5 carriers; raw upstream feed (30,150 rows) carries injected DQ defects mirroring real-world WMS issues.
> **Customer-facing SLA:** orders are promised within **7 calendar days**.

---

## 1. Business problem

Fulfillment is now the largest single cost line outside COGS, and customer-experience scores are dominated by delivery speed and reliability. The COO needs a single dashboard that answers three questions every Monday morning:

1. **Are we hitting the 7-day delivery SLA?** Where are we failing — warehouse, carrier, or product line?
2. **Where are the bottlenecks** — pick & pack, or transit?
3. **Can we trust the operational numbers we report?** The upstream WMS feed has known data-quality issues; we cannot make decisions on dirty inputs.

This project ships an operations-and-DQ dashboard, a documented cleaning pipeline, and a one-row daily DQ scorecard that can be alerted on.

---

## 2. Data description

| Table             | Source            | Rows    | Notes                                                    |
| ----------------- | ----------------- | ------- | -------------------------------------------------------- |
| `shipments_raw`   | Upstream WMS feed | 30,150  | **Intentionally messy**: nulls, duplicates, bad dates, FK violations |
| `shipments`       | Curated           | 30,000  | After applying the cleaning pipeline below               |

**Cleaning pipeline (in `notebooks/01_operations_and_dq.ipynb`):**

1. Drop duplicates on `shipment_id`
2. Drop rows with null `order_date` or null `warehouse_city`
3. Drop rows where `shipping_cost < 0`
4. Drop rows where `carrier NOT IN (DHL, FedEx, UPS, USPS, Local)`
5. Drop rows where `delivery_date < order_date`

The same logic is implemented in SQL (`sql/03_data_quality.sql`) so the dbt / scheduled job in production matches the notebook output exactly.

---

## 3. KPI definitions

| KPI                       | Definition                                                                | Why it matters                             |
| ------------------------- | ------------------------------------------------------------------------- | ------------------------------------------ |
| **On-time %**             | `delivery_date − order_date ≤ 7d`                                         | Headline customer-promise metric           |
| **Failed %**              | Shipment never delivered (`delivery_date IS NULL`)                        | Hard customer impact, refund + reship cost |
| **Avg lead time**         | Mean of `delivery_date − order_date` (days)                               | Speed proxy independent of SLA bucket      |
| **Processing days**       | `ship_date − order_date`                                                  | Warehouse-controlled portion of lead time  |
| **Transit days**          | `delivery_date − ship_date`                                               | Carrier-controlled portion                 |
| **Cost per on-time delivery** | `Total shipping cost / On-time count`                                  | Joint efficiency × reliability metric      |
| **DQ score %**            | `100% − rule-failure rate` across 7 DQ rules                              | Trust in upstream data                     |

---

## 4. Headline results

| KPI                       | Value           |
| ------------------------- | ---------------:|
| Shipments                 | **30,000**      |
| On-time %                 | **85.6%**       |
| Late %                    | **11.8%**       |
| Failed %                  | **2.6%**        |
| Avg lead time             | **5.0 days**    |
| Avg processing time       | **2.0 days**    |
| Avg transit time          | **3.0 days**    |
| Avg shipping cost         | **$13.36**      |
| **DQ score (raw feed)**   | **91.5%**       |

![Operations dashboard](../assets/dashboard_screenshots/project_3_operations_dashboard.png)

The interactive HTML version is at `dashboard/operations_dashboard.html`.

---

## 5. Key findings

### Finding 1 — Sao Paulo is the operations crisis
On-time delivery by warehouse:

| Warehouse        | Region        | Shipments | On-time % | Avg processing | Avg transit |
| ---------------- | ------------- | ---------:| ---------:| --------------:| -----------:|
| **Sao Paulo**    | LATAM         | 3,642     | **38.0%** | 3.3 d          | 4.1 d       |
| Singapore        | APAC          | 5,203     | 76.0%     | 2.3 d          | 4.1 d       |
| Amsterdam        | Europe        | 5,341     | 95.1%     | 2.3 d          | 2.6 d       |
| London           | Europe        | 4,509     | 95.5%     | 2.3 d          | 2.6 d       |
| New York         | NA            | 6,035     | 96.6%     | 1.3 d          | 2.6 d       |
| Los Angeles      | NA            | 5,270     | 97.3%     | 1.3 d          | 2.6 d       |

Sao Paulo's on-time rate is **less than half** the company average. The processing time (3.3 d) is 60% longer than European warehouses, and the long transit adds another day. **Excluding Sao Paulo lifts the global on-time rate from 85.6% to ~91.0%** — a single-site fix.

### Finding 2 — The bottleneck is processing in Sao Paulo, transit everywhere else
Across NA + EU sites, processing is ~1.3-2.3 days and transit is ~2.6 days — both well within budget. In Sao Paulo, processing dominates the SLA breach. This points at a labor / pick-pack capacity issue at one site rather than a systemic carrier problem.

### Finding 3 — The "Local" carrier is bleeding reliability for almost no cost saving
Carrier scorecard:

| Carrier  | Shipments | On-time % | Failed % | Avg cost   |
| -------- | ---------:| ---------:| --------:| ----------:|
| DHL      | 9,068     | **92.2%** | 1.5%     | $13.75     |
| FedEx    | 6,084     | 89.7%     | 2.0%     | $13.75     |
| UPS      | 5,866     | 87.3%     | 2.2%     | $13.79     |
| USPS     | 5,936     | 78.5%     | 3.7%     | $13.75     |
| **Local**| 3,046     | **68.2%** | **6.1%** | $9.80      |

Local saves **~$4 per shipment (~30%)** but **fails 4× as often** as DHL. At an estimated $40 per failed shipment in refunds + reships + CS time, the math is upside-down. USPS is similarly underperforming.

### Finding 4 — Failed deliveries cluster in Sao Paulo + Local carrier
The intersection of the worst warehouse (Sao Paulo) and the worst carrier (Local) accounts for a disproportionate share of `Failed` events. Shifting Sao Paulo's Local volume to DHL alone would cut total failures meaningfully without raising headline cost much.

### Finding 5 — DQ score is 91.5% — *not* good enough for an executive metric
Defects per 30k rows in the raw feed:

| Rule                          | Rows  | % of feed |
| ----------------------------- | -----:| ---------:|
| Missing `warehouse_city`      | 927   | 3.07%     |
| Negative `shipping_cost`      | 597   | 1.98%     |
| Missing `order_date`          | 468   | 1.55%     |
| Unknown carrier code          | 300   | 0.99%     |
| Duplicate `shipment_id`       | 150   | 0.50%     |
| `delivery_date < order_date`  | 128   | 0.42%     |

A 91.5% score means **roughly 1 in 12 rows** triggers at least one rule. The biggest problem is `warehouse_city` completeness — likely a join-key issue against the warehouse master table. Negative cost suggests an upstream sign-flip bug.

### Finding 6 — Lead-time variability is small in EU/NA, large in LATAM
Standard deviation of total lead time is ~0.7 d in NA/EU but >1.5 d in LATAM. Variability is what hurts customer experience even more than mean lead time, because it makes the delivery promise unreliable.

---

## 6. Recommendations

1. **Stand up a Sao Paulo task force.** Diagnose the 3.3-day processing average — labor hours, pick paths, inventory accuracy. Target: 2.0 d processing within 90 days. Single highest-impact action in the entire portfolio.
2. **Migrate Sao Paulo's Local-carrier volume to DHL.** Tolerate the +$4/shipment cost; recover it 5× over in saved refunds and customer trust.
3. **Renegotiate or retire the Local-carrier contract.** Ask for a guaranteed on-time SLA; if they can't commit to >85%, exit.
4. **Fix the upstream `warehouse_city` join.** Single biggest DQ contributor. Once fixed, expect DQ score to lift from 91.5% to ~94.5%.
5. **Add a CHECK constraint to block negative shipping_cost.** Quick database-level guard, prevents the upstream bug from ever landing again.
6. **Promote the DQ score to a top-of-stack alert.** Set a hard SLA: any day below 95% triggers a Slack alert to the data team.
7. **Track on-time % weekly with a 90% target.** Currently 85.6% — the target is achievable inside a quarter if Sao Paulo is fixed.

---

## 7. How to reproduce

```bash
python project_3_operations_analytics/scripts/generate_data.py
psql -f project_3_operations_analytics/sql/01_schema.sql           # optional
jupyter notebook project_3_operations_analytics/notebooks/01_operations_and_dq.ipynb
python project_3_operations_analytics/dashboard/build_dashboard.py
```
