# Business Requirements Document
## Fraud Analytics Data Pipeline — dbt Implementation

**Document Reference:** FAD-BRD-2024-017  
**Version:** 1.2  
**Status:** Approved  
**Owner:** Fraud Data Engineering, Financial Crimes Analytics  
**Last Updated:** 2024-11-12  

---

## 1. Executive Summary

The Fraud Analytics Data Pipeline initiative delivers a structured, auditable data transformation layer to support the Financial Crimes Analytics (FCA) function. The pipeline consolidates raw transactional and customer signals from core banking systems into a set of curated, model-ready datasets that underpin real-time fraud scoring, investigator case management, and regulatory reporting obligations.

This document defines the business requirements, data scope, transformation logic, and source-to-target mappings governing the dbt pipeline implementation.

---

## 2. Business Context and Objectives

The Fraud Detection & Investigations team currently relies on ad-hoc SQL extracts applied directly against operational source systems. This approach introduces latency, inconsistency across analytical outputs, and material risk during peak transaction volumes. The objectives of this initiative are:

1. **Centralise** fraud-relevant data assets within the enterprise data warehouse under a governed transformation layer.
2. **Standardise** field-level definitions and business logic so that all downstream consumers (scoring models, BI dashboards, investigator tooling) operate from a single source of truth.
3. **Enable auditability** of all transformation steps to satisfy internal audit and regulatory review requirements.
4. **Reduce analytical latency** from T+1 batch extracts to near-real-time incremental loads (target: 15-minute refresh cadence for Tier-1 models).
5. **Decouple** model dependencies so that changes to source schemas do not cascade across all downstream consumers simultaneously.

---

## 3. Scope

### 3.1 In Scope

- Ingestion staging models for all four designated source systems (see Section 5)
- Intermediate transformation models applying business rules, entity resolution, and feature derivation
- Three final mart tables consumed by fraud scoring and case management systems
- Data quality tests for all primary keys, referential integrity constraints, and critical business rules
- Full lineage documentation within the dbt project

### 3.2 Out of Scope

- Changes to upstream source systems or their extraction processes
- Real-time streaming ingestion (Kafka / Kinesis layer is a separate workstream)
- Model serving infrastructure for the ML scoring engine
- PII masking at the database layer (handled by the Data Governance platform)

---

## 4. Stakeholders

| Role | Team | Responsibility |
|---|---|---|
| Business Owner | Head of Fraud Operations | Approval of business rules and priority |
| Data Engineering Lead | Financial Crimes Analytics | Pipeline design and delivery |
| Fraud Data Scientist | Model Risk | Feature specification for ML mart |
| Compliance Analyst | Financial Crimes Compliance | Regulatory field mapping (AML/CTF) |
| Platform Engineer | Data Infrastructure | Warehouse environment and CI/CD |
| Internal Audit Liaison | Group Audit | Audit trail and lineage sign-off |

---

## 5. Source Systems

| Source ID | System Name | Schema | Description | Refresh Cadence |
|---|---|---|---|---|
| SRC-01 | Core Banking Ledger | `cbs.raw` | Real-time transaction postings from the core banking platform | Every 15 min (incremental) |
| SRC-02 | Customer Profile Store | `crm.raw` | Customer demographics, KYC status, product holdings | Daily full refresh |
| SRC-03 | Device & Session Intelligence | `dsi.raw` | Digital channel session metadata, device fingerprints, IP signals | Every 15 min (incremental) |
| SRC-04 | Alert & Case Management | `acm.raw` | Fraud alert decisions, investigator case notes, disposition outcomes | Every 30 min (incremental) |

---

## 6. Target Data Architecture

The pipeline follows a three-layer medallion architecture within the dbt project:

```
sources (raw)
    └── staging/          stg_*    — Type casting, renaming, deduplication
            └── intermediate/  int_*    — Business logic, joins, derived features
                    └── marts/         fct_* / dim_*  — Consumption-ready tables
```

### 6.1 Target Tables

| Target Table | Layer | Primary Consumer | Refresh SLA |
|---|---|---|---|
| `fct_fraud_transactions` | Mart | Fraud scoring engine, BI dashboards | 15 min |
| `dim_customer_risk_profile` | Mart | Scoring engine, investigator UI | 1 hour |
| `fct_fraud_alerts` | Mart | Case management system, Compliance reporting | 30 min |

---

## 7. Source-to-Target Mapping

### 7.1 `fct_fraud_transactions`

**Description:** Grain is one row per posted transaction. Combines core transaction data with device session signals and derived fraud feature flags.

**Source Tables:** `cbs.raw.transactions`, `dsi.raw.session_events`

| # | Target Field | Target Type | Source Table | Source Field | Transformation Logic | Nullable | Notes |
|---|---|---|---|---|---|---|---|
| 1 | `transaction_id` | VARCHAR(36) | `cbs.raw.transactions` | `txn_ref_no` | Cast to VARCHAR; assert uniqueness | N | Primary key |
| 2 | `transaction_timestamp_utc` | TIMESTAMP | `cbs.raw.transactions` | `posting_datetime` | Convert from AEST to UTC using `CONVERT_TIMEZONE` | N | |
| 3 | `transaction_date` | DATE | Derived | — | `DATE(transaction_timestamp_utc)` | N | Partition key |
| 4 | `account_id` | VARCHAR(20) | `cbs.raw.transactions` | `acct_no` | Strip leading zeros; cast to VARCHAR | N | FK to `dim_customer_risk_profile` |
| 5 | `channel_code` | VARCHAR(10) | `cbs.raw.transactions` | `txn_channel_cd` | Map: `01`→`ATM`, `02`→`POS`, `03`→`CNP`, `04`→`BRANCH`, `99`→`OTHER` | N | |
| 6 | `transaction_amount_aud` | DECIMAL(18,2) | `cbs.raw.transactions` | `txn_amt` | Divide by 100 (source stored in cents); assert > 0 | N | |
| 7 | `merchant_category_code` | VARCHAR(4) | `cbs.raw.transactions` | `mcc` | Pass through; null-fill with `'0000'` where missing | Y | |
| 8 | `merchant_id` | VARCHAR(20) | `cbs.raw.transactions` | `merchant_ref` | Pass through | Y | |
| 9 | `merchant_country_code` | VARCHAR(3) | `cbs.raw.transactions` | `merch_country` | Uppercase; ISO 3166-1 alpha-3 | Y | |
| 10 | `is_international` | BOOLEAN | Derived | — | `merchant_country_code NOT IN ('AUS') AND merchant_country_code IS NOT NULL` | N | |
| 11 | `session_id` | VARCHAR(36) | `dsi.raw.session_events` | `session_uuid` | Left join on `txn_ref_no = session_txn_ref`; null where no digital session | Y | |
| 12 | `device_fingerprint_hash` | VARCHAR(64) | `dsi.raw.session_events` | `device_fp` | Pass through from joined session record | Y | |
| 13 | `ip_risk_score` | DECIMAL(5,4) | `dsi.raw.session_events` | `ip_risk_score_raw` | Divide by 10000; clamp to [0,1] | Y | Third-party enriched signal |
| 14 | `is_new_device` | BOOLEAN | `dsi.raw.session_events` | `new_device_flag` | Cast `'Y'/'N'` to BOOLEAN; null → FALSE | N | |
| 15 | `velocity_1h_count` | INTEGER | Intermediate derived | — | Count of transactions on same `account_id` in rolling 60-minute window | N | Computed in `int_txn_velocity` |
| 16 | `velocity_24h_amount_aud` | DECIMAL(18,2) | Intermediate derived | — | Sum of `transaction_amount_aud` on same `account_id` in rolling 24-hour window | N | Computed in `int_txn_velocity` |
| 17 | `is_high_risk_mcc` | BOOLEAN | Reference table | `ref.high_risk_mcc` | Join on `merchant_category_code`; TRUE if match found | N | |
| 18 | `pipeline_loaded_at` | TIMESTAMP | System | — | `CURRENT_TIMESTAMP` at model materialisation | N | Audit field |

---

### 7.2 `dim_customer_risk_profile`

**Description:** Grain is one row per active customer account. Snapshot of current risk posture combining KYC status, historical fraud exposure, and behavioural baselines.

**Source Tables:** `crm.raw.customers`, `crm.raw.kyc_assessments`, `acm.raw.fraud_cases`

| # | Target Field | Target Type | Source Table | Source Field | Transformation Logic | Nullable | Notes |
|---|---|---|---|---|---|---|---|
| 1 | `account_id` | VARCHAR(20) | `crm.raw.customers` | `acct_no` | Strip leading zeros; primary key | N | Primary key |
| 2 | `customer_id` | VARCHAR(20) | `crm.raw.customers` | `cust_id` | Pass through | N | |
| 3 | `customer_segment_code` | VARCHAR(10) | `crm.raw.customers` | `seg_cd` | Map: `MASS`→`MASS`, `PREM`→`PREMIUM`, `PRIV`→`PRIVATE`, `BUS`→`BUSINESS` | N | |
| 4 | `account_open_date` | DATE | `crm.raw.customers` | `acct_open_dt` | Cast from VARCHAR `YYYYMMDD` | N | |
| 5 | `account_tenure_days` | INTEGER | Derived | — | `DATEDIFF('day', account_open_date, CURRENT_DATE)` | N | |
| 6 | `kyc_status` | VARCHAR(20) | `crm.raw.kyc_assessments` | `kyc_status_cd` | Latest record per `cust_id` by `assessment_dt`; map: `PASS`→`VERIFIED`, `PEND`→`PENDING`, `FAIL`→`FAILED`, `EXP`→`EXPIRED` | N | |
| 7 | `kyc_last_assessed_date` | DATE | `crm.raw.kyc_assessments` | `assessment_dt` | Latest record per `cust_id` | Y | |
| 8 | `pep_flag` | BOOLEAN | `crm.raw.kyc_assessments` | `pep_ind` | Cast `'1'/'0'` to BOOLEAN | N | Politically Exposed Person indicator |
| 9 | `adverse_media_flag` | BOOLEAN | `crm.raw.kyc_assessments` | `adverse_media_ind` | Cast `'1'/'0'` to BOOLEAN | N | |
| 10 | `lifetime_confirmed_fraud_count` | INTEGER | `acm.raw.fraud_cases` | — | Count of `case_id` where `disposition_cd = 'CONFIRMED'` grouped by `account_id` | N | Default 0 |
| 11 | `lifetime_confirmed_fraud_amount_aud` | DECIMAL(18,2) | `acm.raw.fraud_cases` | `case_loss_amt` | Sum where `disposition_cd = 'CONFIRMED'`; divide by 100 | N | Default 0.00 |
| 12 | `last_fraud_confirmed_date` | DATE | `acm.raw.fraud_cases` | `case_closed_dt` | Max date where `disposition_cd = 'CONFIRMED'` | Y | |
| 13 | `avg_monthly_spend_aud_3m` | DECIMAL(18,2) | Intermediate derived | — | Rolling 90-day average monthly spend from `int_txn_spend_baseline` | Y | |
| 14 | `dominant_txn_country` | VARCHAR(3) | Intermediate derived | — | Modal `merchant_country_code` in last 90 days | Y | |
| 15 | `risk_tier` | VARCHAR(10) | Derived | — | Rule-based: `HIGH` if `pep_flag=TRUE OR lifetime_confirmed_fraud_count > 0`; `MEDIUM` if `kyc_status IN ('PENDING','EXPIRED')`; else `LOW` | N | Reviewed quarterly by Compliance |
| 16 | `pipeline_loaded_at` | TIMESTAMP | System | — | `CURRENT_TIMESTAMP` at model materialisation | N | Audit field |

---

### 7.3 `fct_fraud_alerts`

**Description:** Grain is one row per fraud alert event. Captures alert generation, investigator disposition, and case linkage for compliance and feedback loop purposes.

**Source Tables:** `acm.raw.alerts`, `acm.raw.fraud_cases`, `acm.raw.investigator_actions`

| # | Target Field | Target Type | Source Table | Source Field | Transformation Logic | Nullable | Notes |
|---|---|---|---|---|---|---|---|
| 1 | `alert_id` | VARCHAR(36) | `acm.raw.alerts` | `alert_uuid` | Assert uniqueness | N | Primary key |
| 2 | `transaction_id` | VARCHAR(36) | `acm.raw.alerts` | `txn_ref_no` | FK to `fct_fraud_transactions` | N | |
| 3 | `account_id` | VARCHAR(20) | `acm.raw.alerts` | `acct_no` | Strip leading zeros | N | FK to `dim_customer_risk_profile` |
| 4 | `alert_generated_at` | TIMESTAMP | `acm.raw.alerts` | `alert_ts` | Convert AEST to UTC | N | |
| 5 | `alert_rule_id` | VARCHAR(20) | `acm.raw.alerts` | `rule_cd` | Pass through | N | References rules catalogue |
| 6 | `alert_rule_description` | VARCHAR(200) | `acm.raw.alerts` | `rule_desc` | Pass through | Y | |
| 7 | `alert_score` | DECIMAL(5,4) | `acm.raw.alerts` | `ml_score` | Divide by 10000; clamp to [0,1]; null where rule-based only | Y | ML model output |
| 8 | `alert_priority` | VARCHAR(10) | Derived | — | `HIGH` if `alert_score >= 0.85 OR rule_cd IN ('RUL-007','RUL-011')`; `MEDIUM` if score >= 0.60; else `LOW` | N | |
| 9 | `case_id` | VARCHAR(36) | `acm.raw.fraud_cases` | `case_uuid` | Left join on `alert_uuid`; null if alert not yet worked | Y | |
| 10 | `case_opened_at` | TIMESTAMP | `acm.raw.fraud_cases` | `case_open_ts` | Convert AEST to UTC | Y | |
| 11 | `case_closed_at` | TIMESTAMP | `acm.raw.fraud_cases` | `case_close_ts` | Convert AEST to UTC | Y | |
| 12 | `disposition_code` | VARCHAR(20) | `acm.raw.fraud_cases` | `disposition_cd` | Map: `CONF`→`CONFIRMED`, `DECL`→`DECLINED`, `PEND`→`PENDING`, `ESCL`→`ESCALATED` | Y | |
| 13 | `investigator_id` | VARCHAR(20) | `acm.raw.investigator_actions` | `investigator_emp_id` | Latest action per `case_id` | Y | |
| 14 | `time_to_disposition_minutes` | INTEGER | Derived | — | `DATEDIFF('minute', alert_generated_at, case_closed_at)`; null if open | Y | SLA monitoring metric |
| 15 | `is_true_positive` | BOOLEAN | Derived | — | `disposition_code = 'CONFIRMED'` | N | Default FALSE |
| 16 | `is_false_positive` | BOOLEAN | Derived | — | `disposition_code = 'DECLINED'` | N | Default FALSE |
| 17 | `feedback_loop_eligible` | BOOLEAN | Derived | — | `disposition_code IN ('CONFIRMED','DECLINED') AND case_closed_at IS NOT NULL` | N | Used to flag records for model retraining |
| 18 | `pipeline_loaded_at` | TIMESTAMP | System | — | `CURRENT_TIMESTAMP` at model materialisation | N | Audit field |

---

## 8. Data Quality Requirements

The following dbt tests must pass in CI before any model is deployed to production.

| Test Category | Requirement |
|---|---|
| Uniqueness | All primary key fields (`transaction_id`, `account_id`, `alert_id`) must be unique |
| Not-null | All fields marked `Nullable: N` must have zero null records |
| Referential integrity | `fct_fraud_transactions.account_id` must exist in `dim_customer_risk_profile.account_id` |
| Referential integrity | `fct_fraud_alerts.transaction_id` must exist in `fct_fraud_transactions.transaction_id` |
| Accepted values | `channel_code` must be one of `ATM`, `POS`, `CNP`, `BRANCH`, `OTHER` |
| Accepted values | `risk_tier` must be one of `HIGH`, `MEDIUM`, `LOW` |
| Accepted values | `disposition_code` must be one of `CONFIRMED`, `DECLINED`, `PENDING`, `ESCALATED` or null |
| Range check | `ip_risk_score` must be between 0 and 1 |
| Range check | `alert_score` must be between 0 and 1 |
| Range check | `transaction_amount_aud` must be greater than 0 |
| Freshness | `fct_fraud_transactions` source freshness must not exceed 30 minutes |
| Freshness | `fct_fraud_alerts` source freshness must not exceed 60 minutes |
| Row count | Staging row counts must be within ±5% of prior run (anomaly test) |

---

## 9. Non-Functional Requirements

| Category | Requirement |
|---|---|
| Latency | Tier-1 marts (`fct_fraud_transactions`, `fct_fraud_alerts`) must complete incremental runs within 10 minutes of source data availability |
| Availability | Pipeline must achieve 99.5% monthly uptime during business hours (06:00–22:00 AEST) |
| Data retention | Mart tables retain 36 months of rolling history; staging tables retain 7 days |
| Auditability | All model runs must emit row-level metadata (`pipeline_loaded_at`, dbt run ID) to support audit trace |
| Access control | Mart tables are read-accessible to Fraud Operations, Model Risk, and Compliance. Write access is restricted to the service account used by the dbt pipeline |
| PII handling | Fields `customer_id`, `account_id`, `investigator_id` are classified as Restricted. Column-level access controls must be applied at the warehouse layer |

---

## 10. Assumptions and Dependencies

1. Source system extraction (CDC or scheduled batch) to the raw landing zone is owned by the Platform Engineering team and is outside the scope of this pipeline.
2. The `ref.high_risk_mcc` reference table is maintained by the Fraud Operations team and will be published to the warehouse on a monthly basis.
3. Timezone handling assumes all source timestamps are recorded in AEST (UTC+10) unless explicitly documented otherwise by the source system owner.
4. The ML score field (`acm.raw.alerts.ml_score`) will be null for alerts generated by deterministic rules only. This is expected behaviour and not a data quality defect.
5. KYC assessment records may contain multiple entries per customer. The pipeline always selects the most recent record by `assessment_dt`.

---

## 11. Open Items

| ID | Description | Owner | Target Resolution |
|---|---|---|---|
| OI-01 | Confirm whether `dsi.raw.session_events` join key (`session_txn_ref`) is guaranteed to be populated for all CNP transactions | Platform Engineering | 2024-11-20 |
| OI-02 | Agree SLA for `dim_customer_risk_profile` refresh cadence with Fraud scoring team | Fraud Data Science | 2024-11-22 |
| OI-03 | Validate `risk_tier` derivation logic with Compliance before go-live | Compliance Analyst | 2024-11-29 |

---

*This document is classified Internal Use Only. Distribution is restricted to named stakeholders and authorised project contributors.*