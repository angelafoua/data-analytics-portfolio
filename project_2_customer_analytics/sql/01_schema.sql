-- =====================================================================
-- Project 2: Customer Behavior & Retention — Schema
-- =====================================================================

DROP TABLE IF EXISTS transactions;
DROP TABLE IF EXISTS customers;

CREATE TABLE customers (
    customer_id    VARCHAR(16)  PRIMARY KEY,
    signup_date    DATE         NOT NULL,
    country        VARCHAR(8)   NOT NULL,
    acq_channel    VARCHAR(32)  NOT NULL,
    plan           VARCHAR(16)  NOT NULL,
    monthly_price  NUMERIC(10,2) NOT NULL
);

CREATE TABLE transactions (
    transaction_id   BIGINT       PRIMARY KEY,
    customer_id      VARCHAR(16)  REFERENCES customers (customer_id),
    transaction_date DATE         NOT NULL,
    plan             VARCHAR(16)  NOT NULL,
    amount           NUMERIC(10,2) NOT NULL,
    type             VARCHAR(32)  NOT NULL
);

CREATE INDEX idx_tx_customer ON transactions (customer_id);
CREATE INDEX idx_tx_date     ON transactions (transaction_date);
