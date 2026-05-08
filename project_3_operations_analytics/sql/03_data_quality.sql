-- =====================================================================
-- Project 3: Data Quality monitoring on the raw shipments feed
-- =====================================================================
-- These checks form the basis of a daily DQ scorecard. Each query is
-- intended to return a single row that can be unioned into a metrics
-- table or shipped to a monitoring tool (e.g. Great Expectations,
-- dbt tests, Monte Carlo).
-- =====================================================================


-- ---------------------------------------------------------------------
-- 1. Completeness: % of rows missing any of the critical fields
-- ---------------------------------------------------------------------
SELECT
    'completeness' AS check_name,
    COUNT(*)       AS rows_total,
    SUM(CASE WHEN order_date     IS NULL THEN 1 ELSE 0 END) AS missing_order_date,
    SUM(CASE WHEN warehouse_city IS NULL THEN 1 ELSE 0 END) AS missing_warehouse_city,
    SUM(CASE WHEN delivery_date  IS NULL THEN 1 ELSE 0 END) AS missing_delivery_date,
    ROUND(100.0 *
          SUM(CASE WHEN order_date IS NULL OR warehouse_city IS NULL THEN 1 ELSE 0 END)
          / COUNT(*), 3) AS critical_null_rate_pct
FROM shipments_raw;


-- ---------------------------------------------------------------------
-- 2. Uniqueness: duplicate primary keys
-- ---------------------------------------------------------------------
WITH dups AS (
    SELECT shipment_id, COUNT(*) AS n
    FROM   shipments_raw
    GROUP BY shipment_id
    HAVING COUNT(*) > 1
)
SELECT
    'uniqueness'                                     AS check_name,
    (SELECT COUNT(*) FROM shipments_raw)             AS rows_total,
    (SELECT COUNT(*) FROM dups)                      AS duplicate_keys,
    (SELECT COALESCE(SUM(n - 1), 0) FROM dups)       AS extra_duplicate_rows;


-- ---------------------------------------------------------------------
-- 3. Validity: out-of-range values
-- ---------------------------------------------------------------------
SELECT
    'validity'                                                    AS check_name,
    SUM(CASE WHEN delivery_date < order_date THEN 1 ELSE 0 END)  AS bad_date_order,
    SUM(CASE WHEN shipping_cost < 0          THEN 1 ELSE 0 END)  AS negative_cost,
    SUM(CASE WHEN total_days   > 30          THEN 1 ELSE 0 END)  AS extreme_lead_time
FROM shipments_raw;


-- ---------------------------------------------------------------------
-- 4. Referential integrity: unknown carrier codes
-- ---------------------------------------------------------------------
SELECT
    'referential_integrity'                                       AS check_name,
    COUNT(*)                                                      AS unknown_carrier_rows
FROM   shipments_raw
WHERE  carrier NOT IN ('DHL', 'FedEx', 'UPS', 'USPS', 'Local');


-- ---------------------------------------------------------------------
-- 5. Freshness: % of rows received with a >24h delay
--    (placeholder query — assumes a load_timestamp column in production)
-- ---------------------------------------------------------------------
-- SELECT
--     'freshness' AS check_name,
--     ROUND(100.0 * SUM(CASE WHEN load_timestamp - ship_date > INTERVAL '24 hours'
--                            THEN 1 ELSE 0 END) / COUNT(*), 3) AS late_arrival_pct
-- FROM shipments_raw;


-- ---------------------------------------------------------------------
-- 6. Single-row DQ scorecard combining the checks above
--    (Useful for dashboard tile / alerting)
-- ---------------------------------------------------------------------
WITH base AS (
    SELECT
        COUNT(*) AS rows_total,
        SUM(CASE WHEN order_date     IS NULL THEN 1 ELSE 0 END) AS n_null_order_date,
        SUM(CASE WHEN warehouse_city IS NULL THEN 1 ELSE 0 END) AS n_null_wh_city,
        SUM(CASE WHEN delivery_date  IS NULL THEN 1 ELSE 0 END) AS n_null_delivery,
        SUM(CASE WHEN delivery_date < order_date THEN 1 ELSE 0 END) AS n_bad_date,
        SUM(CASE WHEN shipping_cost < 0          THEN 1 ELSE 0 END) AS n_neg_cost,
        SUM(CASE WHEN carrier NOT IN ('DHL','FedEx','UPS','USPS','Local')
                 THEN 1 ELSE 0 END)                                 AS n_unknown_carrier
    FROM shipments_raw
),
dups AS (
    SELECT COUNT(*) AS n_dup_keys FROM (
        SELECT shipment_id FROM shipments_raw
        GROUP BY shipment_id HAVING COUNT(*) > 1
    ) d
)
SELECT
    rows_total,
    n_null_order_date, n_null_wh_city, n_null_delivery,
    n_bad_date, n_neg_cost, n_unknown_carrier, n_dup_keys,
    ROUND(100.0 - 100.0 *
          (n_null_order_date + n_null_wh_city + n_bad_date +
           n_neg_cost + n_unknown_carrier + n_dup_keys)::numeric
          / rows_total, 3) AS dq_score_pct
FROM base, dups;
