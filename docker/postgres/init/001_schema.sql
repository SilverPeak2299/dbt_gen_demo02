-- Postgres uses a single schema namespace, so Snowflake-style namespaces such as
-- cbs.raw are represented here as cbs_raw, crm_raw, dsi_raw, and acm_raw.

CREATE SCHEMA IF NOT EXISTS cbs_raw;
CREATE SCHEMA IF NOT EXISTS crm_raw;
CREATE SCHEMA IF NOT EXISTS dsi_raw;
CREATE SCHEMA IF NOT EXISTS acm_raw;

CREATE TABLE IF NOT EXISTS cbs_raw.transactions (
    txn_ref_no VARCHAR(36) PRIMARY KEY,
    posting_datetime VARCHAR(26) NOT NULL,
    acct_no VARCHAR(25) NOT NULL,
    txn_channel_cd CHAR(2) NOT NULL,
    txn_amt INTEGER NOT NULL,
    txn_dr_cr_ind CHAR(1) NOT NULL,
    mcc VARCHAR(4),
    merchant_ref VARCHAR(20),
    merch_country CHAR(3),
    reversal_ind CHAR(1) NOT NULL,
    orig_txn_ref_no VARCHAR(36),
    load_timestamp TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS crm_raw.customers (
    acct_no VARCHAR(25) PRIMARY KEY,
    cust_id VARCHAR(20) NOT NULL,
    acct_open_dt VARCHAR(8) NOT NULL,
    acct_status_cd CHAR(1) NOT NULL,
    seg_cd VARCHAR(10) NOT NULL,
    product_cd VARCHAR(10) NOT NULL,
    branch_cd VARCHAR(6) NOT NULL,
    snapshot_dt DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS crm_raw.kyc_assessments (
    assessment_id VARCHAR(36) PRIMARY KEY,
    cust_id VARCHAR(20) NOT NULL,
    assessment_dt DATE NOT NULL,
    kyc_status_cd VARCHAR(10) NOT NULL,
    pep_ind CHAR(1) NOT NULL,
    adverse_media_ind CHAR(1) NOT NULL,
    sanction_screen_dt DATE NOT NULL,
    analyst_id VARCHAR(20) NOT NULL
);

CREATE TABLE IF NOT EXISTS dsi_raw.session_events (
    session_uuid VARCHAR(36) PRIMARY KEY,
    session_txn_ref VARCHAR(36) NOT NULL,
    session_start_ts TIMESTAMP NOT NULL,
    session_end_ts TIMESTAMP,
    device_fp VARCHAR(64) NOT NULL,
    new_device_flag CHAR(1) NOT NULL,
    ip_address_hash VARCHAR(64) NOT NULL,
    ip_risk_score_raw INTEGER NOT NULL,
    geo_country_code VARCHAR(3) NOT NULL,
    load_timestamp TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS acm_raw.alerts (
    alert_uuid VARCHAR(36) PRIMARY KEY,
    txn_ref_no VARCHAR(36) NOT NULL,
    acct_no VARCHAR(25) NOT NULL,
    alert_ts VARCHAR(26) NOT NULL,
    rule_cd VARCHAR(20) NOT NULL,
    rule_desc VARCHAR(200),
    ml_score INTEGER,
    alert_status_cd VARCHAR(10) NOT NULL,
    load_timestamp TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS acm_raw.fraud_cases (
    case_uuid VARCHAR(36) PRIMARY KEY,
    alert_uuid VARCHAR(36) NOT NULL,
    acct_no VARCHAR(25) NOT NULL,
    case_open_ts VARCHAR(26) NOT NULL,
    case_close_ts VARCHAR(26),
    disposition_cd VARCHAR(10) NOT NULL,
    case_loss_amt INTEGER,
    fraud_type_cd VARCHAR(20),
    load_timestamp TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS acm_raw.investigator_actions (
    action_id VARCHAR(36) PRIMARY KEY,
    case_uuid VARCHAR(36) NOT NULL,
    investigator_emp_id VARCHAR(20) NOT NULL,
    action_ts TIMESTAMP NOT NULL,
    action_type_cd VARCHAR(20) NOT NULL,
    action_notes TEXT,
    load_timestamp TIMESTAMP NOT NULL
);
