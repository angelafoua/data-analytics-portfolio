-- =====================================================================
-- Project 1: Sales Performance — Headline KPIs
-- =====================================================================
-- Each query returns one of the metrics surfaced on the executive
-- dashboard. Filters can be applied by date / region / channel.
-- =====================================================================


-- ---------------------------------------------------------------------
-- 1. Net revenue, gross profit, gross margin (excluding cancelled lines)
-- ---------------------------------------------------------------------
SELECT
    ROUND(SUM(oi.gross_revenue)::numeric, 2)                                AS net_revenue,
    ROUND(SUM(oi.gross_profit)::numeric, 2)                                 AS gross_profit,
    ROUND(SUM(oi.gross_profit)::numeric / NULLIF(SUM(oi.gross_revenue), 0)
          * 100, 2)                                                         AS gross_margin_pct
FROM   order_items   oi
JOIN   orders        o ON o.order_id = oi.order_id
WHERE  o.status <> 'Cancelled';


-- ---------------------------------------------------------------------
-- 2. Average Order Value (AOV)
-- ---------------------------------------------------------------------
WITH order_totals AS (
    SELECT  o.order_id,
            SUM(oi.gross_revenue) AS order_value
    FROM    orders        o
    JOIN    order_items   oi ON oi.order_id = o.order_id
    WHERE   o.status = 'Completed'
    GROUP BY o.order_id
)
SELECT  ROUND(AVG(order_value)::numeric, 2) AS aov
FROM    order_totals;


-- ---------------------------------------------------------------------
-- 3. Return rate (% of order lines flagged 'Returned')
-- ---------------------------------------------------------------------
SELECT
    ROUND(100.0 * SUM(CASE WHEN o.status = 'Returned' THEN 1 ELSE 0 END)
          / COUNT(*), 2) AS return_rate_pct
FROM   orders o;


-- ---------------------------------------------------------------------
-- 4. Active customers in the last 90 days
-- ---------------------------------------------------------------------
SELECT  COUNT(DISTINCT customer_id) AS active_customers_90d
FROM    orders
WHERE   order_date >= (SELECT MAX(order_date) FROM orders) - INTERVAL '90 days'
  AND   status = 'Completed';
