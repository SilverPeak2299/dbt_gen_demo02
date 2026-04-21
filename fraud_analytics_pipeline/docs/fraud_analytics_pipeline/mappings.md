---
title: Source To Target Mappings
sidebar_label: Mappings
---

# Source To Target Mappings

The full column-level mapping is published with the package at [`mappings/source_to_target.md`](../../mappings/source_to_target.html).

## Coverage Summary

| Target Model | Columns Mapped | Primary Sources |
| --- | --- | --- |
| `fct_fraud_transactions` | 18 | `cbs_raw.transactions`, `dsi_raw.session_events`, `ref.high_risk_mcc` |
| `dim_customer_risk_profile` | 16 | `crm_raw.customers`, `crm_raw.kyc_assessments`, `acm_raw.fraud_cases`, `cbs_raw.transactions` |
| `fct_fraud_alerts` | 18 | `acm_raw.alerts`, `acm_raw.fraud_cases`, `acm_raw.investigator_actions` |

## Review Notes

- Derived fields explicitly reference the intermediate model that implements them where that matters for traceability.
- The mapping keeps the empty `high_risk_mcc` seed visible rather than replacing it with invented MCC values.
- Fields with unresolved governance decisions are called out in the assumptions page and design document.
