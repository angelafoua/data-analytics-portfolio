-- =====================================================================
-- Project 3: Operations & Data Quality — Schema
-- =====================================================================
-- Two tables: a "raw" landing table that mirrors what arrives from the
-- upstream WMS feed (deliberately messy), and a "clean" curated table.
-- =====================================================================

DROP TABLE IF EXISTS shipments_raw;
DROP TABLE IF EXISTS shipments;

CREATE TABLE shipments_raw (
    shipment_id     VARCHAR(16),
    order_id        VARCHAR(16),
    order_date      DATE,
    ship_date       DATE,
    delivery_date   DATE,
    warehouse_id    VARCHAR(16),
    warehouse_city  VARCHAR(64),
    region          VARCHAR(32),
    carrier         VARCHAR(32),
    product_line    VARCHAR(32),
    processing_days NUMERIC(8,2),
    transit_days    NUMERIC(8,2),
    total_days      NUMERIC(8,2),
    shipping_cost   NUMERIC(10,2),
    status          VARCHAR(16)
);

CREATE TABLE shipments (
    shipment_id     VARCHAR(16) PRIMARY KEY,
    order_id        VARCHAR(16) NOT NULL,
    order_date      DATE        NOT NULL,
    ship_date       DATE        NOT NULL,
    delivery_date   DATE,
    warehouse_id    VARCHAR(16) NOT NULL,
    warehouse_city  VARCHAR(64) NOT NULL,
    region          VARCHAR(32) NOT NULL,
    carrier         VARCHAR(32) NOT NULL,
    product_line    VARCHAR(32) NOT NULL,
    processing_days NUMERIC(8,2) NOT NULL,
    transit_days    NUMERIC(8,2) NOT NULL,
    total_days      NUMERIC(8,2) NOT NULL,
    shipping_cost   NUMERIC(10,2) NOT NULL,
    status          VARCHAR(16) NOT NULL CHECK (status IN ('On-time','Late','Failed'))
);

CREATE INDEX idx_ship_date     ON shipments (ship_date);
CREATE INDEX idx_ship_carrier  ON shipments (carrier);
CREATE INDEX idx_ship_wh       ON shipments (warehouse_id);
