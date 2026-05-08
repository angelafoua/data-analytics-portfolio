-- =====================================================================
-- Project 1: Sales Performance Analytics — Schema
-- =====================================================================
-- Star-schema modeled on a typical e-commerce data warehouse. The CSVs
-- under ../data/ load directly into these tables. PostgreSQL syntax is
-- used; works with minor changes on Snowflake / BigQuery / Redshift.
-- =====================================================================

DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS daily_funnel;

CREATE TABLE customers (
    customer_id  VARCHAR(16) PRIMARY KEY,
    signup_date  DATE        NOT NULL,
    country      VARCHAR(64) NOT NULL,
    region       VARCHAR(32) NOT NULL,
    segment      VARCHAR(32) NOT NULL
);

CREATE TABLE products (
    product_id    VARCHAR(16)  PRIMARY KEY,
    product_name  VARCHAR(64)  NOT NULL,
    category      VARCHAR(32)  NOT NULL,
    unit_cost     NUMERIC(10,2) NOT NULL,
    unit_price    NUMERIC(10,2) NOT NULL
);

CREATE TABLE orders (
    order_id     VARCHAR(16) PRIMARY KEY,
    order_date   DATE        NOT NULL,
    customer_id  VARCHAR(16) REFERENCES customers (customer_id),
    channel      VARCHAR(32) NOT NULL,
    status       VARCHAR(16) NOT NULL
);

CREATE TABLE order_items (
    order_item_id BIGINT      PRIMARY KEY,
    order_id      VARCHAR(16) REFERENCES orders   (order_id),
    product_id    VARCHAR(16) REFERENCES products (product_id),
    quantity      INTEGER     NOT NULL,
    unit_price    NUMERIC(10,2) NOT NULL,
    unit_cost     NUMERIC(10,2) NOT NULL,
    gross_revenue NUMERIC(12,2) NOT NULL,
    cost          NUMERIC(12,2) NOT NULL,
    gross_profit  NUMERIC(12,2) NOT NULL
);

CREATE TABLE daily_funnel (
    date         DATE        NOT NULL,
    channel      VARCHAR(32) NOT NULL,
    sessions     INTEGER     NOT NULL,
    add_to_cart  INTEGER     NOT NULL,
    checkout     INTEGER     NOT NULL,
    purchases    INTEGER     NOT NULL,
    PRIMARY KEY (date, channel)
);

CREATE INDEX idx_orders_date     ON orders (order_date);
CREATE INDEX idx_orders_customer ON orders (customer_id);
CREATE INDEX idx_items_order     ON order_items (order_id);
CREATE INDEX idx_items_product   ON order_items (product_id);
