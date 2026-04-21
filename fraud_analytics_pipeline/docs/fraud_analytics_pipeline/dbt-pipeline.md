---
title: DBT Pipeline
sidebar_label: DBT Pipeline
---

# DBT Pipeline

## Model Layers

| Layer | Models | Purpose |
| --- | --- | --- |
| Staging | `stg_cbs_transactions`, `stg_crm_customers`, `stg_crm_kyc_assessments`, `stg_dsi_session_events`, `stg_acm_alerts`, `stg_acm_fraud_cases`, `stg_acm_investigator_actions` | Normalize types, trim keys, parse dates, convert timestamps to UTC, and deduplicate raw rows. |
| Intermediate | `int_txn_velocity`, `int_txn_spend_baseline`, `int_customer_latest_kyc`, `int_customer_fraud_exposure`, `int_alert_case_actions` | Build reusable behavioral and case-management logic away from final marts. |
| Marts | `fct_fraud_transactions`, `dim_customer_risk_profile`, `fct_fraud_alerts` | Publish consumer-facing facts and dimensions that match the BRD outputs. |

## Notable SQL Choices

- Postgres timestamp conversion uses `::timestamptz at time zone 'UTC'`.
- Rolling features use interval window frames on the staged transaction timestamps.
- Fact models are configured incremental-ready, but the prototype currently scans staged inputs end-to-end until a production late-arrival policy is agreed.
- The alert mart enriches alerts with the latest investigator action instead of every case event.

## Test Coverage

| Category | Coverage |
| --- | --- |
| Keys | `unique` and `not_null` tests on primary keys in sources and marts |
| Referential integrity | Transaction-to-dimension and alert-to-transaction relationships |
| Accepted values | Channel, risk tier, alert priority, disposition |
| Range checks | Custom singular tests for `ip_risk_score`, `alert_score`, and positive transaction amount |
| Freshness | Raw-source freshness rules in `models/sources.yml` |

## Operational Gap

The BRD asks for a row-count anomaly test versus the prior run. That requires persistent run history and is documented as a follow-up rather than hard-coded into this static review package.
