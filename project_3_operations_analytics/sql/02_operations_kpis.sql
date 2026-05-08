-- =====================================================================
-- Project 3: Operations Efficiency — KPI queries
-- =====================================================================
-- Customer-facing SLA: orders are promised within 5 calendar days.
-- =====================================================================


-- ---------------------------------------------------------------------
-- 1. Headline: on-time-in-full %, average lead time, failure rate
-- ---------------------------------------------------------------------
SELECT
    COUNT(*)                                                         AS shipments,
    ROUND(100.0 * SUM(CASE WHEN status = 'On-time' THEN 1 ELSE 0 END)
                / COUNT(*), 2)                                       AS on_time_pct,
    ROUND(100.0 * SUM(CASE WHEN status = 'Late' THEN 1 ELSE 0 END)
                / COUNT(*), 2)                                       AS late_pct,
    ROUND(100.0 * SUM(CASE WHEN status = 'Failed' THEN 1 ELSE 0 END)
                / COUNT(*), 2)                                       AS failed_pct,
    ROUND(AVG(total_days)::numeric, 2)                               AS avg_lead_time_days,
    ROUND(AVG(processing_days)::numeric, 2)                          AS avg_processing_days,
    ROUND(AVG(transit_days)::numeric, 2)                             AS avg_transit_days,
    ROUND(AVG(shipping_cost)::numeric, 2)                            AS avg_shipping_cost
FROM   shipments;


-- ---------------------------------------------------------------------
-- 2. SLA performance by warehouse (where bottlenecks live)
-- ---------------------------------------------------------------------
SELECT
    warehouse_id,
    warehouse_city,
    COUNT(*)                                                         AS shipments,
    ROUND(100.0 * SUM(CASE WHEN status = 'On-time' THEN 1 ELSE 0 END)
                / COUNT(*), 2)                                       AS on_time_pct,
    ROUND(AVG(processing_days)::numeric, 2)                          AS avg_processing_days,
    ROUND(AVG(transit_days)::numeric, 2)                             AS avg_transit_days,
    ROUND(AVG(total_days)::numeric, 2)                               AS avg_lead_time
FROM   shipments
GROUP BY warehouse_id, warehouse_city
ORDER BY on_time_pct ASC;   -- worst first


-- ---------------------------------------------------------------------
-- 3. Carrier scorecard
-- ---------------------------------------------------------------------
SELECT
    carrier,
    COUNT(*)                                                         AS shipments,
    ROUND(100.0 * SUM(CASE WHEN status = 'On-time' THEN 1 ELSE 0 END)
                / COUNT(*), 2)                                       AS on_time_pct,
    ROUND(100.0 * SUM(CASE WHEN status = 'Failed'  THEN 1 ELSE 0 END)
                / COUNT(*), 2)                                       AS failed_pct,
    ROUND(AVG(transit_days)::numeric, 2)                             AS avg_transit_days,
    ROUND(AVG(shipping_cost)::numeric, 2)                            AS avg_cost,
    ROUND((AVG(shipping_cost) /
           NULLIF(SUM(CASE WHEN status = 'On-time' THEN 1 ELSE 0 END), 0))::numeric, 2)
                                                                     AS cost_per_on_time_delivery
FROM   shipments
GROUP BY carrier
ORDER BY on_time_pct DESC;


-- ---------------------------------------------------------------------
-- 4. Daily SLA trend (rolling 30-day on-time %)
-- ---------------------------------------------------------------------
WITH daily AS (
    SELECT
        ship_date,
        SUM(CASE WHEN status = 'On-time' THEN 1 ELSE 0 END)::float AS on_time,
        COUNT(*)                                                   AS total
    FROM   shipments
    GROUP BY ship_date
)
SELECT
    ship_date,
    ROUND((100.0 * on_time / total)::numeric, 2) AS on_time_pct,
    ROUND((100.0 * SUM(on_time) OVER (ORDER BY ship_date
                                       ROWS BETWEEN 29 PRECEDING AND CURRENT ROW)
                  / SUM(total) OVER (ORDER BY ship_date
                                       ROWS BETWEEN 29 PRECEDING AND CURRENT ROW)
          )::numeric, 2)                          AS rolling_30d_on_time_pct
FROM   daily
ORDER BY ship_date;


-- ---------------------------------------------------------------------
-- 5. Bottleneck attribution: where is the delay coming from?
-- ---------------------------------------------------------------------
SELECT
    'Processing'  AS stage,
    ROUND(AVG(processing_days)::numeric, 2)                AS avg_days,
    ROUND(STDDEV_POP(processing_days)::numeric, 2)         AS stddev_days,
    ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP
          (ORDER BY processing_days)::numeric, 2)          AS p95_days
FROM shipments
UNION ALL
SELECT
    'Transit',
    ROUND(AVG(transit_days)::numeric, 2),
    ROUND(STDDEV_POP(transit_days)::numeric, 2),
    ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP
          (ORDER BY transit_days)::numeric, 2)
FROM shipments;
