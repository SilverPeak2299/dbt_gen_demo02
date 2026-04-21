---
title: Assumptions And Open Questions
sidebar_label: Assumptions
---

# Assumptions And Open Questions

## Confirmed Facts

- The source-of-truth identifiers for this repo are the local Postgres schemas: `cbs_raw`, `crm_raw`, `dsi_raw`, and `acm_raw`.
- `dbt` is installed locally, but the repository did not already contain a dbt project or a docs site.
- Static review documentation is the safest publish target because it does not require profiles, secrets, or a warehouse connection in CI.

## Assumptions Used In Generation

- The package targets Postgres SQL for this review phase.
- `fct_fraud_transactions` keeps only debit, non-reversal transactions.
- `dim_customer_risk_profile` excludes only closed accounts so fact relationships remain intact.
- The empty `high_risk_mcc` seed is a placeholder for the governed Fraud Operations reference feed.

## Open Questions

| ID | Question | Impact |
| --- | --- | --- |
| `OI-01` | Is `session_txn_ref` populated for every digital CNP transaction that should carry session data? | Determines whether null session joins indicate expected sparsity or upstream loss. |
| `OI-02` | Should dormant accounts remain in `dim_customer_risk_profile`, or should the dimension be restricted to strictly active accounts? | Affects referential integrity and dashboard populations. |
| `OI-03` | Should `FAILED` KYC map above `LOW` in `risk_tier` despite the literal BRD logic? | Affects customer prioritization and alerting thresholds. |
| `OI-04` | When will the governed high-risk MCC reference be available for seed replacement? | Affects the correctness of `is_high_risk_mcc`. |
