---
title: Data Definition
sidebar_label: Data Definition
---

# Data Definition

## Curated Datasets

| Model | Business Grain | Semantic Role | Caveats |
| --- | --- | --- | --- |
| `fct_fraud_transactions` | One debit, non-reversal transaction | Core transaction feature set for fraud scoring and monitoring | Session data is expected to be null for non-digital channels. |
| `dim_customer_risk_profile` | One current non-closed account | Current customer risk posture combining KYC, exposure, and spend behavior | Closed accounts are excluded; dormant handling remains a business confirmation item. |
| `fct_fraud_alerts` | One alert event | Alert outcomes, investigator ownership, and feedback-loop readiness | Some alerts will have no linked case or disposition yet. |

## Key Measures And Dimensions

| Field | Meaning |
| --- | --- |
| `transaction_amount_aud` | Transaction amount in Australian dollars after cents-to-dollars conversion |
| `velocity_1h_count` | Number of debit, non-reversal transactions on the account in the prior hour including the current row |
| `velocity_24h_amount_aud` | Rolling 24-hour debit amount on the account including the current row |
| `avg_monthly_spend_aud_3m` | Last-90-day spend divided by three months |
| `risk_tier` | Rule-based `HIGH/MEDIUM/LOW` classification from KYC and confirmed fraud exposure |
| `alert_priority` | Rule-based `HIGH/MEDIUM/LOW` alert severity for investigator triage |
| `feedback_loop_eligible` | Closed and labeled alert ready for model feedback or retraining pipelines |

## Restricted Fields

| Field | Classification | Handling |
| --- | --- | --- |
| `customer_id` | Restricted | Exposed in the customer dimension; warehouse column controls still required |
| `account_id` | Restricted | Exposed across marts; warehouse column controls still required |
| `investigator_id` | Restricted internal PII | Exposed only in `fct_fraud_alerts`; case notes remain out of the mart layer |

## Exclusions

- Raw `action_notes`, `ip_address_hash`, and `load_timestamp` fields remain outside the final marts.
- The high-risk MCC list is represented by an empty placeholder seed until the governed reference is supplied.
