---
title: Fraud Analytics Pipeline Overview
sidebar_label: Overview
---

# Fraud Analytics Pipeline Overview

This package turns the requirements in `docs/brd.md` and the semantic source notes in `docs/source-info.md` into a standalone dbt review package under `fraud_analytics_pipeline/`.

## Delivery Shape

| Deliverable | Location |
| --- | --- |
| DBT project scaffold | `fraud_analytics_pipeline/dbt_project.yml` |
| Models and tests | `fraud_analytics_pipeline/models/`, `fraud_analytics_pipeline/tests/` |
| Reference seed placeholder | `fraud_analytics_pipeline/seeds/high_risk_mcc.csv` |
| Mapping and design docs | `fraud_analytics_pipeline/mappings/`, `fraud_analytics_pipeline/design/` |
| Static doc builder | `fraud_analytics_pipeline/scripts/build_static_docs.py` |
| GitHub Pages workflow | `.github/workflows/publish-static-docs.yml` |

## Selected Runtime Context

| Decision | Value | Evidence |
| --- | --- | --- |
| SQL dialect | Postgres | Local `postgres:16` stack and Postgres schema names in `docs/source-info.md` |
| Publishing mode | Static review docs | No Docusaurus project or lockfile in the repo |
| DBT project shape | Standalone package | No root `dbt_project.yml` existed before generation |

## Output Datasets

| Model | Grain | Primary Consumers |
| --- | --- | --- |
| `fct_fraud_transactions` | One debit, non-reversal transaction | Fraud scoring, dashboards |
| `dim_customer_risk_profile` | One current non-closed account | Scoring engine, investigator UI |
| `fct_fraud_alerts` | One fraud alert event | Case management, compliance reporting |

## Review Priorities

- Confirm the debit-only transaction scope and dormant-account handling.
- Replace the placeholder high-risk MCC seed with the governed Fraud Operations extract.
- Confirm whether `FAILED` KYC should map to a higher `risk_tier` than the literal BRD rule currently allows.
