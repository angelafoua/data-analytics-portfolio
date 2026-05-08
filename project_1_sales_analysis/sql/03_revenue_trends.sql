-- =====================================================================
-- Project 1: Sales Performance — Revenue trend analyses
-- =====================================================================


-- ---------------------------------------------------------------------
-- 1. Monthly revenue with month-over-month growth
-- ---------------------------------------------------------------------
WITH monthly AS (
    SELECT  DATE_TRUNC('month', o.order_date)::date AS month,
            SUM(oi.gross_revenue)                   AS revenue,
            SUM(oi.gross_profit)                    AS gross_profit
    FROM    orders        o
    JOIN    order_items   oi ON oi.order_id = o.order_id
    WHERE   o.status <> 'Cancelled'
    GROUP BY 1
)
SELECT
    month,
    revenue,
    gross_profit,
    LAG(revenue)  OVER (ORDER BY month) AS prev_month_revenue,
    ROUND(100.0 * (revenue - LAG(revenue) OVER (ORDER BY month))
                / NULLIF(LAG(revenue) OVER (ORDER BY month), 0), 2)
        AS mom_growth_pct
FROM   monthly
ORDER BY month;


-- ---------------------------------------------------------------------
-- 2. Year-over-year growth by month
-- ---------------------------------------------------------------------
WITH monthly AS (
    SELECT  EXTRACT(YEAR  FROM o.order_date)::int AS year,
            EXTRACT(MONTH FROM o.order_date)::int AS month,
            SUM(oi.gross_revenue)                 AS revenue
    FROM    orders        o
    JOIN    order_items   oi ON oi.order_id = o.order_id
    WHERE   o.status <> 'Cancelled'
    GROUP BY 1, 2
)
SELECT
    curr.year,
    curr.month,
    curr.revenue,
    prev.revenue AS prev_year_revenue,
    ROUND(100.0 * (curr.revenue - prev.revenue) / NULLIF(prev.revenue, 0), 2)
        AS yoy_growth_pct
FROM       monthly curr
LEFT JOIN  monthly prev
       ON  prev.year  = curr.year  - 1
      AND  prev.month = curr.month
ORDER BY   curr.year, curr.month;


-- ---------------------------------------------------------------------
-- 3. Trailing-30-day revenue (rolling)
-- ---------------------------------------------------------------------
WITH daily AS (
    SELECT  o.order_date,
            SUM(oi.gross_revenue) AS revenue
    FROM    orders        o
    JOIN    order_items   oi ON oi.order_id = o.order_id
    WHERE   o.status <> 'Cancelled'
    GROUP BY o.order_date
)
SELECT
    order_date,
    revenue,
    SUM(revenue) OVER (
        ORDER BY order_date
        ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
    ) AS revenue_trailing_30d
FROM   daily
ORDER BY order_date;
