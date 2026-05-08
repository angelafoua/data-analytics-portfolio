-- =====================================================================
-- Project 1: Sales Performance — Breakdowns
-- =====================================================================


-- ---------------------------------------------------------------------
-- 1. Revenue and margin by category
-- ---------------------------------------------------------------------
SELECT
    p.category,
    SUM(oi.gross_revenue)                                         AS revenue,
    SUM(oi.gross_profit)                                          AS gross_profit,
    ROUND(100.0 * SUM(oi.gross_profit)
                / NULLIF(SUM(oi.gross_revenue), 0), 2)            AS margin_pct,
    SUM(oi.quantity)                                              AS units_sold
FROM   order_items oi
JOIN   orders      o ON o.order_id   = oi.order_id
JOIN   products    p ON p.product_id = oi.product_id
WHERE  o.status <> 'Cancelled'
GROUP BY p.category
ORDER BY revenue DESC;


-- ---------------------------------------------------------------------
-- 2. Top 10 products by revenue (with rank within category)
-- ---------------------------------------------------------------------
SELECT *
FROM (
    SELECT
        p.product_id,
        p.product_name,
        p.category,
        SUM(oi.gross_revenue)                                 AS revenue,
        SUM(oi.quantity)                                      AS units_sold,
        ROW_NUMBER() OVER (PARTITION BY p.category
                           ORDER BY SUM(oi.gross_revenue) DESC) AS rank_in_category
    FROM   order_items oi
    JOIN   orders      o ON o.order_id   = oi.order_id
    JOIN   products    p ON p.product_id = oi.product_id
    WHERE  o.status <> 'Cancelled'
    GROUP BY p.product_id, p.product_name, p.category
) t
ORDER BY revenue DESC
LIMIT 10;


-- ---------------------------------------------------------------------
-- 3. Regional sales breakdown with share of total
-- ---------------------------------------------------------------------
WITH region_rev AS (
    SELECT  c.region,
            SUM(oi.gross_revenue) AS revenue,
            COUNT(DISTINCT o.customer_id) AS active_customers
    FROM    order_items oi
    JOIN    orders      o ON o.order_id    = oi.order_id
    JOIN    customers   c ON c.customer_id = o.customer_id
    WHERE   o.status <> 'Cancelled'
    GROUP BY c.region
)
SELECT
    region,
    revenue,
    active_customers,
    ROUND(100.0 * revenue / SUM(revenue) OVER (), 2) AS share_of_total_pct
FROM   region_rev
ORDER BY revenue DESC;


-- ---------------------------------------------------------------------
-- 4. Top 20 customers (Pareto check: do they drive 20% of revenue?)
-- ---------------------------------------------------------------------
WITH cust_rev AS (
    SELECT  c.customer_id,
            c.country,
            c.segment,
            SUM(oi.gross_revenue) AS revenue
    FROM    order_items oi
    JOIN    orders      o ON o.order_id    = oi.order_id
    JOIN    customers   c ON c.customer_id = o.customer_id
    WHERE   o.status = 'Completed'
    GROUP BY c.customer_id, c.country, c.segment
)
SELECT
    customer_id,
    country,
    segment,
    revenue,
    ROUND(100.0 * revenue / SUM(revenue) OVER (), 4) AS share_of_total_pct
FROM   cust_rev
ORDER BY revenue DESC
LIMIT 20;


-- ---------------------------------------------------------------------
-- 5. Channel funnel conversion rates
-- ---------------------------------------------------------------------
SELECT
    channel,
    SUM(sessions)     AS sessions,
    SUM(add_to_cart)  AS add_to_cart,
    SUM(checkout)     AS checkout,
    SUM(purchases)    AS purchases,
    ROUND(100.0 * SUM(add_to_cart) / NULLIF(SUM(sessions),    0), 2) AS atc_rate_pct,
    ROUND(100.0 * SUM(checkout)    / NULLIF(SUM(add_to_cart), 0), 2) AS checkout_rate_pct,
    ROUND(100.0 * SUM(purchases)   / NULLIF(SUM(checkout),    0), 2) AS purchase_rate_pct,
    ROUND(100.0 * SUM(purchases)   / NULLIF(SUM(sessions),    0), 2) AS overall_conv_pct
FROM   daily_funnel
GROUP BY channel
ORDER BY purchases DESC;
