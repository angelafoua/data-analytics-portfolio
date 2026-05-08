-- =====================================================================
-- Project 2: Customer Behavior & Retention — Churn, LTV, Segmentation
-- =====================================================================


-- ---------------------------------------------------------------------
-- 1. Monthly churn rate
--    A customer is "churned" in month M if they paid in M-1 but not M.
-- ---------------------------------------------------------------------
WITH active AS (
    SELECT DISTINCT
           customer_id,
           DATE_TRUNC('month', transaction_date)::date AS month
    FROM   transactions
),
month_pairs AS (
    SELECT
        a.month,
        a.customer_id,
        LEAD(a.month) OVER (PARTITION BY a.customer_id ORDER BY a.month) AS next_month
    FROM active a
)
SELECT
    month + INTERVAL '1 month' AS churn_month,
    COUNT(*) FILTER (
        WHERE next_month IS NULL OR next_month > month + INTERVAL '1 month'
    )                          AS churned_customers,
    COUNT(*)                   AS active_in_prev_month,
    ROUND(100.0 * COUNT(*) FILTER (
        WHERE next_month IS NULL OR next_month > month + INTERVAL '1 month'
    ) / COUNT(*), 2)           AS churn_rate_pct
FROM   month_pairs
GROUP BY month
ORDER BY churn_month;


-- ---------------------------------------------------------------------
-- 2. Customer-level summary: orders, revenue, lifespan, status
-- ---------------------------------------------------------------------
WITH cust_tx AS (
    SELECT
        customer_id,
        MIN(transaction_date)                 AS first_tx,
        MAX(transaction_date)                 AS last_tx,
        COUNT(*)                              AS tx_count,
        SUM(amount)                           AS total_revenue,
        AVG(amount)                           AS avg_tx_value
    FROM   transactions
    GROUP BY customer_id
)
SELECT
    c.customer_id,
    c.plan,
    c.acq_channel,
    c.country,
    t.first_tx,
    t.last_tx,
    t.tx_count,
    t.total_revenue,
    ROUND(t.avg_tx_value::numeric, 2)         AS avg_tx_value,
    -- months between first and last paid event (lifespan proxy)
    ((EXTRACT(YEAR  FROM t.last_tx) - EXTRACT(YEAR  FROM t.first_tx)) * 12
   + (EXTRACT(MONTH FROM t.last_tx) - EXTRACT(MONTH FROM t.first_tx)))::int
                                              AS lifespan_months,
    -- "Active" if they paid in the most recent 60 days, else "Churned"
    CASE
        WHEN t.last_tx >= (SELECT MAX(transaction_date) FROM transactions) - INTERVAL '60 days'
        THEN 'Active'
        ELSE 'Churned'
    END                                       AS status
FROM   customers c
JOIN   cust_tx   t USING (customer_id);


-- ---------------------------------------------------------------------
-- 3. LTV by acquisition channel (mean of customer total revenue)
-- ---------------------------------------------------------------------
WITH cust_rev AS (
    SELECT customer_id, SUM(amount) AS total_revenue
    FROM   transactions
    GROUP BY customer_id
)
SELECT
    c.acq_channel,
    COUNT(*)                                  AS customers,
    ROUND(AVG(r.total_revenue)::numeric, 2)   AS avg_ltv,
    ROUND(SUM(r.total_revenue)::numeric, 2)   AS total_revenue
FROM   customers   c
JOIN   cust_rev    r USING (customer_id)
GROUP BY c.acq_channel
ORDER BY avg_ltv DESC;


-- ---------------------------------------------------------------------
-- 4. RFM-lite segmentation (Recency / Frequency / Monetary tertiles)
-- ---------------------------------------------------------------------
WITH base AS (
    SELECT
        customer_id,
        (SELECT MAX(transaction_date) FROM transactions)
             - MAX(transaction_date)                 AS recency,
        COUNT(*)                                     AS frequency,
        SUM(amount)                                  AS monetary
    FROM transactions
    GROUP BY customer_id
),
scored AS (
    SELECT
        customer_id,
        NTILE(3) OVER (ORDER BY recency   ASC)  AS r_score,  -- recent = best
        NTILE(3) OVER (ORDER BY frequency DESC) AS f_score,
        NTILE(3) OVER (ORDER BY monetary  DESC) AS m_score
    FROM base
)
SELECT
    CASE
        WHEN r_score = 1 AND f_score = 1 AND m_score = 1 THEN 'Champions'
        WHEN r_score = 1 AND f_score >= 2                THEN 'Promising'
        WHEN r_score = 3 AND f_score = 1                 THEN 'At Risk'
        WHEN r_score = 3                                 THEN 'Lost'
        ELSE                                                  'Loyal'
    END                          AS segment,
    COUNT(*)                     AS customers
FROM   scored
GROUP BY segment
ORDER BY customers DESC;


-- ---------------------------------------------------------------------
-- 5. New vs. returning customers per month (paid event basis)
-- ---------------------------------------------------------------------
WITH first_tx AS (
    SELECT customer_id, MIN(transaction_date) AS first_date
    FROM   transactions
    GROUP BY customer_id
)
SELECT
    DATE_TRUNC('month', t.transaction_date)::date AS month,
    COUNT(DISTINCT CASE
        WHEN DATE_TRUNC('month', f.first_date) = DATE_TRUNC('month', t.transaction_date)
        THEN t.customer_id END)                   AS new_customers,
    COUNT(DISTINCT CASE
        WHEN DATE_TRUNC('month', f.first_date) < DATE_TRUNC('month', t.transaction_date)
        THEN t.customer_id END)                   AS returning_customers,
    COUNT(DISTINCT t.customer_id)                 AS active_customers
FROM   transactions t
JOIN   first_tx     f USING (customer_id)
GROUP BY 1
ORDER BY 1;
