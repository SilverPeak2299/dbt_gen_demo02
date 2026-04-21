# Source Table Semantic Context
## Fraud Analytics Data Pipeline — FAD-BRD-2024-017

**Purpose:** This document provides natural-language semantic descriptions of each source table and its fields. It is intended for use as structured context when generating dbt staging models, column descriptions, or data catalogue entries programmatically.

## Local Prototype Status

This repository now includes a local Postgres prototype of the raw source layer. The original Snowflake-style namespaces have been mapped to Postgres schemas as follows:

| Original Namespace | Local Postgres Schema |
|---|---|
| `cbs.raw` | `cbs_raw` |
| `crm.raw` | `crm_raw` |
| `dsi.raw` | `dsi_raw` |
| `acm.raw` | `acm_raw` |

The current bootstrap dataset includes the following seeded row counts:

| Local Table | Seeded Rows |
|---|---|
| `cbs_raw.transactions` | 6 |
| `crm_raw.customers` | 5 |
| `crm_raw.kyc_assessments` | 5 |
| `dsi_raw.session_events` | 3 |
| `acm_raw.alerts` | 5 |
| `acm_raw.fraud_cases` | 3 |
| `acm_raw.investigator_actions` | 6 |

The descriptions below remain the semantic source-of-truth for dbt generation, but the table identifiers have been updated to match the local prototype.

---

## SRC-01 — `cbs_raw.transactions`

**System:** Core Banking Ledger  
**Description:** This table contains every financial transaction posted to the core banking system. Each row represents a single transaction posting event. Records are written in near-real-time as transactions are authorised and settled. The table is append-only; corrections and reversals appear as new rows with a reversal indicator rather than updates to existing rows. This is the primary source for all transaction-level fraud analysis.

| Column | Data Type | Description |
|---|---|---|
| `txn_ref_no` | VARCHAR(36) | Unique identifier assigned by the core banking system at the point of transaction origination. This is the natural key for a transaction and maps to `transaction_id` in the mart layer. Values are UUIDs in practice but stored as VARCHAR. |
| `posting_datetime` | VARCHAR(26) | Timestamp at which the transaction was posted to the ledger. Stored as a string in ISO 8601 format (`YYYY-MM-DDTHH:MM:SS+10:00`). All timestamps are in AEST (UTC+10). Must be cast to TIMESTAMP and converted to UTC in staging. |
| `acct_no` | VARCHAR(25) | The bank account number of the customer initiating the transaction. In the local prototype these values are zero-padded to 25 characters. Leading zeros should be stripped in staging. Maps to `account_id` in the mart layer and is the primary join key to the customer dimension. |
| `txn_channel_cd` | CHAR(2) | Two-character numeric code indicating the channel through which the transaction was initiated. Known values: `01` = ATM withdrawal, `02` = Point-of-Sale (POS) terminal, `03` = Card-Not-Present (CNP, i.e. online), `04` = Branch teller, `99` = Other or unclassified. Values outside this set should be mapped to `OTHER` and flagged for investigation. |
| `txn_amt` | INTEGER | Transaction amount in Australian cents (integer). A value of `1050` represents AUD 10.50. Must be divided by 100 to produce a decimal dollar amount. Always positive; credit and debit directionality is indicated by `txn_dr_cr_ind`. |
| `txn_dr_cr_ind` | CHAR(1) | Indicates whether the transaction is a debit (`D`) or credit (`C`) from the perspective of the customer account. Fraud models are primarily concerned with debit transactions. |
| `mcc` | VARCHAR(4) | Merchant Category Code (ISO 18245) identifying the type of business at which the transaction occurred. May be null for ATM and branch transactions. A null value should be coerced to `'0000'` in the mart layer to preserve join-ability with the MCC reference table. |
| `merchant_ref` | VARCHAR(20) | Internal merchant identifier assigned by the card scheme or bank. Not globally unique across schemes. May be null for non-merchant transactions (e.g. ATM cash withdrawals). |
| `merch_country` | CHAR(3) | ISO 3166-1 alpha-3 country code of the merchant's registered country. May be null for domestic ATM transactions. Should be stored in uppercase. Used to derive the `is_international` flag. |
| `reversal_ind` | CHAR(1) | Indicates whether this row is a reversal of a prior transaction. `Y` = reversal, `N` = original posting. Fraud models should typically exclude reversal rows or handle them as a separate event type. |
| `orig_txn_ref_no` | VARCHAR(36) | For reversal rows (`reversal_ind = 'Y'`), contains the `txn_ref_no` of the original transaction being reversed. Null for non-reversal rows. |
| `load_timestamp` | TIMESTAMP | The timestamp at which this record was written to the raw landing zone by the extract process. Used for incremental model filtering. Not business-meaningful; do not expose in marts. |

---

## SRC-02 — `crm_raw.customers`

**System:** Customer Profile Store  
**Description:** This table holds the canonical customer and account record for all active and recently closed accounts held at the bank. Each row represents one account. A single customer (`cust_id`) may have multiple accounts. The table is refreshed daily via a full snapshot load; the most recent load represents the current state. Historical account states are not retained in this table — point-in-time history is available separately through the Customer History Vault (out of scope for this pipeline).

| Column | Data Type | Description |
|---|---|---|
| `acct_no` | VARCHAR(25) | The bank account number, zero-padded to 25 characters. Primary key of this table. Corresponds to `acct_no` in `cbs_raw.transactions` and is the core join key across the fraud data model. |
| `cust_id` | VARCHAR(20) | The bank's internal customer identifier. A customer may hold multiple accounts. Used to aggregate fraud exposure at the customer level and to join to KYC assessments. |
| `acct_open_dt` | VARCHAR(8) | Account opening date stored as an 8-character string in `YYYYMMDD` format. Must be cast to DATE in staging. Used to calculate account tenure, which is a significant predictor in fraud models (newer accounts carry higher risk). |
| `acct_status_cd` | CHAR(1) | Account status code. `A` = Active, `D` = Dormant, `C` = Closed, `S` = Suspended. Fraud analytics should generally focus on active accounts but may include dormant accounts for detection purposes. |
| `seg_cd` | VARCHAR(10) | Customer segment assigned by the CRM system. Known values: `MASS` (standard retail), `PREM` (premium retail), `PRIV` (private banking), `BUS` (business banking). Used to contextualise transaction behaviour (e.g. higher average spend is expected for PRIV customers). |
| `product_cd` | VARCHAR(10) | Product type associated with the account (e.g. `CHQ` for cheque account, `SAV` for savings, `CC` for credit card). Relevant for channel-specific fraud rule targeting. |
| `branch_cd` | VARCHAR(6) | BSB-equivalent branch code where the account is domiciled. May be used for geographic clustering analysis. |
| `snapshot_dt` | DATE | The date on which this full-snapshot record was loaded. Used to confirm recency of the customer data and for debugging data quality issues. |

---

## SRC-02 — `crm_raw.kyc_assessments`

**System:** Customer Profile Store  
**Description:** This table stores Know Your Customer (KYC) assessment records for each customer. A customer may have multiple rows reflecting successive assessments over time. Each row represents the outcome of one assessment event. The pipeline must select the most recent record per `cust_id` based on `assessment_dt`. KYC status and associated flags are material to fraud risk scoring and are required for compliance with AML/CTF obligations.

| Column | Data Type | Description |
|---|---|---|
| `assessment_id` | VARCHAR(36) | Unique identifier for the KYC assessment event. Primary key of this table. |
| `cust_id` | VARCHAR(20) | The bank's internal customer identifier. Foreign key to `crm_raw.customers.cust_id`. A customer may have multiple assessment rows; always use the most recent. |
| `assessment_dt` | DATE | The date on which the KYC assessment was completed. Used to select the latest record per customer. |
| `kyc_status_cd` | VARCHAR(10) | Outcome of the KYC assessment. Known values: `PASS` (identity verified), `PEND` (assessment in progress or awaiting documentation), `FAIL` (identity could not be verified), `EXP` (prior passing assessment has expired and re-assessment is required). Customers with `FAIL` or `EXP` status represent elevated risk. |
| `pep_ind` | CHAR(1) | Politically Exposed Person indicator. `1` = customer is identified as a PEP or is closely associated with a PEP; `0` = no PEP association identified. PEP status is a regulatory risk flag and must be surfaced in the customer risk profile. |
| `adverse_media_ind` | CHAR(1) | Adverse media screening indicator. `1` = customer has been identified in adverse media sources associated with financial crime; `0` = no adverse media identified. Updated periodically by the Compliance screening process. |
| `sanction_screen_dt` | DATE | Date on which the most recent sanctions list screening was completed. A stale date (older than 90 days) may indicate the customer's screening is overdue. |
| `analyst_id` | VARCHAR(20) | Employee ID of the compliance analyst who completed or approved the assessment. Not exposed in marts; retained for audit purposes in staging. |

---

## SRC-03 — `dsi_raw.session_events`

**System:** Device & Session Intelligence  
**Description:** This table captures session and device metadata from the bank's digital banking channels (mobile app and internet banking). Each row represents one session event that was associated with a transaction originating from a digital channel. Rows are only present for Card-Not-Present (CNP) and certain mobile-initiated transactions; ATM, POS, and branch transactions will not have matching records. The join from `cbs_raw.transactions` to this table is a left join; null session data is expected and is not a data quality defect for non-digital channels.

| Column | Data Type | Description |
|---|---|---|
| `session_uuid` | VARCHAR(36) | Unique identifier for the digital session. Primary key of this table. Maps to `session_id` in `fct_fraud_transactions`. |
| `session_txn_ref` | VARCHAR(36) | The `txn_ref_no` from the core banking system that was initiated during this session. Used as the join key to `cbs_raw.transactions`. Note: one session may theoretically generate multiple transactions; in practice this is rare and the pipeline takes the first matching record. |
| `session_start_ts` | TIMESTAMP | UTC timestamp when the digital session was initiated. |
| `session_end_ts` | TIMESTAMP | UTC timestamp when the session was terminated (by logout or timeout). May be null if the session was abandoned. |
| `device_fp` | VARCHAR(64) | Hashed device fingerprint generated by the client-side SDK. Represents a combination of device hardware, OS, and browser attributes. Used to detect account takeover patterns where a transaction originates from a device not previously associated with the account. |
| `new_device_flag` | CHAR(1) | `Y` if the `device_fp` has not been observed for this `acct_no` in the prior 90 days; `N` otherwise. A new device at transaction time is a significant fraud signal. |
| `ip_address_hash` | VARCHAR(64) | Hashed IP address of the device at session initiation. Not exposed in marts in raw form. Used internally for velocity and geolocation analysis. |
| `ip_risk_score_raw` | INTEGER | IP reputation risk score supplied by a third-party threat intelligence feed. Stored as an integer 0–10000 representing a probability of 0.0000–1.0000. Must be divided by 10000 in staging. Higher scores indicate greater likelihood that the IP address is associated with fraud, VPN use, or proxy/anonymisation services. |
| `geo_country_code` | VARCHAR(3) | ISO 3166-1 alpha-3 country code of the IP address's resolved geolocation. Used to identify impossible travel scenarios when compared against `merchant_country_code`. |
| `load_timestamp` | TIMESTAMP | Timestamp at which this record was written to the raw landing zone. Used for incremental model filtering. |

---

## SRC-04 — `acm_raw.alerts`

**System:** Alert & Case Management  
**Description:** This table records every fraud alert generated by the bank's fraud detection systems. An alert is created when a transaction (or pattern of transactions) is flagged by a deterministic rule, a machine learning model, or both. Each row represents one alert. Alerts are subsequently triaged by the fraud operations team; their decisions are recorded in `acm_raw.fraud_cases` and `acm_raw.investigator_actions`. This table is the primary source for measuring detection system performance (precision, recall, false positive rate).

| Column | Data Type | Description |
|---|---|---|
| `alert_uuid` | VARCHAR(36) | Unique identifier for the alert event. Primary key of this table. Maps to `alert_id` in `fct_fraud_alerts`. |
| `txn_ref_no` | VARCHAR(36) | The `txn_ref_no` from the core banking system that triggered the alert. Foreign key to `cbs_raw.transactions`. |
| `acct_no` | VARCHAR(25) | The account number associated with the triggering transaction. Zero-padded; strip leading zeros in staging. |
| `alert_ts` | VARCHAR(26) | Timestamp when the alert was generated, in AEST ISO 8601 format. Must be cast to TIMESTAMP and converted to UTC. |
| `rule_cd` | VARCHAR(20) | Code identifying the rule or model that generated the alert. Deterministic rules follow the format `RUL-XXX`; ML model alerts follow the format `MDL-XXX`. Multiple alerts may be generated for the same transaction by different rules. |
| `rule_desc` | VARCHAR(200) | Human-readable description of the rule or model that generated the alert. May be null for legacy rule codes not yet documented in the rules catalogue. |
| `ml_score` | INTEGER | For ML model-generated alerts (`rule_cd` starting with `MDL-`), this field contains the model's fraud probability score scaled 0–10000. Null for deterministic rule alerts. Must be divided by 10000 in staging to produce a decimal probability. |
| `alert_status_cd` | VARCHAR(10) | Current status of the alert in the case management workflow. `NEW` = unworked, `OPEN` = assigned to investigator, `CLOSED` = disposition recorded. |
| `load_timestamp` | TIMESTAMP | Timestamp at which this record was written to the raw landing zone. Used for incremental model filtering. |

---

## SRC-04 — `acm_raw.fraud_cases`

**System:** Alert & Case Management  
**Description:** This table records investigator case records linked to one or more fraud alerts. A case is opened when an alert is escalated for human review. Each row represents one case. Cases may be linked to multiple alerts, but the pipeline joins on a one-to-one basis (one case per alert's primary trigger). The disposition outcome (`disposition_cd`) is the ground-truth label used for model retraining and regulatory reporting.

| Column | Data Type | Description |
|---|---|---|
| `case_uuid` | VARCHAR(36) | Unique identifier for the fraud case. Primary key of this table. Maps to `case_id` in `fct_fraud_alerts`. |
| `alert_uuid` | VARCHAR(36) | Foreign key to `acm_raw.alerts.alert_uuid`. Represents the primary alert that triggered case creation. |
| `acct_no` | VARCHAR(25) | The account number associated with the case. |
| `case_open_ts` | VARCHAR(26) | AEST timestamp when the case was opened by an investigator. Cast and convert to UTC in staging. |
| `case_close_ts` | VARCHAR(26) | AEST timestamp when the case was closed with a final disposition. Null for open cases. Cast and convert to UTC in staging. |
| `disposition_cd` | VARCHAR(10) | The investigator's final determination. `CONF` = confirmed fraud (true positive), `DECL` = declined / not fraud (false positive), `PEND` = pending review, `ESCL` = escalated to a higher tier for further review. This is the primary outcome label for the pipeline. |
| `case_loss_amt` | INTEGER | The financial loss amount associated with the case in Australian cents. Populated only for confirmed fraud cases (`disposition_cd = 'CONF'`). Null otherwise. Divide by 100 to produce decimal AUD in staging. |
| `fraud_type_cd` | VARCHAR(20) | Classification of the fraud type as determined by the investigator. Example values: `CNP_FRAUD`, `ACCOUNT_TAKEOVER`, `ID_THEFT`, `SCAM_AUTHORISED`, `CARD_SKIMMING`. Used for stratified analysis and reporting. |
| `load_timestamp` | TIMESTAMP | Timestamp at which this record was written to the raw landing zone. |

---

## SRC-04 — `acm_raw.investigator_actions`

**System:** Alert & Case Management  
**Description:** This table is an audit log of all actions taken by fraud investigators on a case. Each row represents one investigator action event. Multiple actions may exist per case as the investigation progresses. The pipeline uses this table to identify the assigned investigator (last action per case) and to support investigator workload and SLA reporting. It is not a primary source for fraud outcome data.

| Column | Data Type | Description |
|---|---|---|
| `action_id` | VARCHAR(36) | Unique identifier for the investigator action. Primary key of this table. |
| `case_uuid` | VARCHAR(36) | Foreign key to `acm_raw.fraud_cases.case_uuid`. |
| `investigator_emp_id` | VARCHAR(20) | The employee ID of the investigator who performed the action. Maps to `investigator_id` in `fct_fraud_alerts`. This field is classified as Restricted PII (internal). |
| `action_ts` | TIMESTAMP | UTC timestamp when the action was recorded. Used to identify the most recent action per case and to calculate time-to-action SLA metrics. |
| `action_type_cd` | VARCHAR(20) | Type of action performed. Example values: `ASSIGNED`, `NOTE_ADDED`, `STATUS_CHANGED`, `DISPOSITION_SET`, `ESCALATED`. |
| `action_notes` | TEXT | Free-text notes entered by the investigator. Contains sensitive case detail. Not exposed in any mart layer. Retained at staging for investigator tooling consumption only. |
| `load_timestamp` | TIMESTAMP | Timestamp at which this record was written to the raw landing zone. |

---

*This document is intended for use as structured semantic input to automated pipeline generation tooling. Field descriptions represent agreed business definitions as of the document version date and should be treated as the authoritative source for dbt column-level `description` metadata. The local Postgres table names above are the identifiers to use when wiring sources in this repository.*
