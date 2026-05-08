-- =====================================================================
-- Project 2: Customer Behavior & Retention
-- Cohort retention matrix (signup month × months-since-signup)
-- =====================================================================
--
-- Reads the transactions table and produces a percentage matrix that can
-- be pivoted to render the classic cohort heatmap.
-- =====================================================================

WITH cust_cohort AS (
    -- Each customer's signup month becomes their cohort label.
    SELECT  customer_id,
            DATE_TRUNC('month', signup_date)::date AS cohort_month
    FROM    customers
),
activity AS (
    -- Months in which each customer paid (one row per cust × active month).
    SELECT DISTINCT
            customer_id,
            DATE_TRUNC('month', transaction_date)::date AS active_month
    FROM    transactions
),
cohort_long AS (
    SELECT
        c.cohort_month,
        ((EXTRACT(YEAR  FROM a.active_month) - EXTRACT(YEAR  FROM c.cohort_month)) * 12
       + (EXTRACT(MONTH FROM a.active_month) - EXTRACT(MONTH FROM c.cohort_month)))::int
                                                AS month_index,
        COUNT(DISTINCT a.customer_id)           AS customers
    FROM   activity     a
    JOIN   cust_cohort  c USING (customer_id)
    GROUP BY 1, 2
),
cohort_size AS (
    SELECT  cohort_month, COUNT(*) AS cohort_size
    FROM    cust_cohort
    GROUP BY cohort_month
)
SELECT
    cl.cohort_month,
    cl.month_index,
    cl.customers,
    cs.cohort_size,
    ROUND(100.0 * cl.customers / cs.cohort_size, 2) AS retention_pct
FROM   cohort_long cl
JOIN   cohort_size cs USING (cohort_month)
ORDER BY cl.cohort_month, cl.month_index;
