# Source-to-Target Mapping

## fct_fraud_transactions

| Target Model | Target Column | Source Table | Source Column | Transformation Logic | Business Rule Reference | Data Quality Expectation | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `fct_fraud_transactions` | `transaction_id` | `cbs_raw.transactions` | `txn_ref_no` | Rename to curated primary key. | BRD 7.1.1 | Unique, not null | Debit, non-reversal scope is applied at the model level. |
| `fct_fraud_transactions` | `transaction_timestamp_utc` | `cbs_raw.transactions` | `posting_datetime` | Cast ISO 8601 AEST text to `timestamptz` and convert to UTC. | BRD 7.1.2 | Not null | Postgres implementation replaces Snowflake `CONVERT_TIMEZONE`. |
| `fct_fraud_transactions` | `transaction_date` | Derived | - | Cast `transaction_timestamp_utc` to `date`. | BRD 7.1.3 | Not null | Used as the date grain attribute. |
| `fct_fraud_transactions` | `account_id` | `cbs_raw.transactions` | `acct_no` | Strip leading zeros with `ltrim`. | BRD 7.1.4 | Not null; relationship to `dim_customer_risk_profile.account_id` | Uses the local Postgres prototype key shape. |
| `fct_fraud_transactions` | `channel_code` | `cbs_raw.transactions` | `txn_channel_cd` | Map `01/02/03/04/99` to `ATM/POS/CNP/BRANCH/OTHER`; all unexpected values become `OTHER`. | BRD 7.1.5 | Not null; accepted values | Unexpected codes are normalized and should be investigated upstream. |
| `fct_fraud_transactions` | `transaction_amount_aud` | `cbs_raw.transactions` | `txn_amt` | Divide integer cents by `100.0`. | BRD 7.1.6 | Not null; must be greater than 0 | The mart retains only debit, non-reversal transactions. |
| `fct_fraud_transactions` | `merchant_category_code` | `cbs_raw.transactions` | `mcc` | Trim and coalesce null or blank values to `'0000'`. | BRD 7.1.7 | Nullable by requirement | Coercion preserves joinability to the MCC reference. |
| `fct_fraud_transactions` | `merchant_id` | `cbs_raw.transactions` | `merchant_ref` | Trim and pass through. | BRD 7.1.8 | Nullable | Null for non-merchant channels. |
| `fct_fraud_transactions` | `merchant_country_code` | `cbs_raw.transactions` | `merch_country` | Trim and uppercase. | BRD 7.1.9 | Nullable | Stored as ISO alpha-3. |
| `fct_fraud_transactions` | `is_international` | Derived | - | `merchant_country_code is not null and merchant_country_code <> 'AUS'`. | BRD 7.1.10 | Not null | Domestic nulls remain `FALSE`. |
| `fct_fraud_transactions` | `session_id` | `dsi_raw.session_events` | `session_uuid` | Left join first matching session on `session_txn_ref = txn_ref_no`. | BRD 7.1.11 | Nullable | First session is chosen by earliest `session_start_ts`. |
| `fct_fraud_transactions` | `device_fingerprint_hash` | `dsi_raw.session_events` | `device_fp` | Pass through from the first matching session. | BRD 7.1.12 | Nullable | Null is expected for non-digital transactions. |
| `fct_fraud_transactions` | `ip_risk_score` | `dsi_raw.session_events` | `ip_risk_score_raw` | Divide by `10000.0` and clamp to `[0,1]`. | BRD 7.1.13 | Nullable; range check `0..1` | Preserved as null where no session or no score exists. |
| `fct_fraud_transactions` | `is_new_device` | `dsi_raw.session_events` | `new_device_flag` | Map `Y/N` to boolean and default null joins to `FALSE`. | BRD 7.1.14 | Not null | Null session joins are expected. |
| `fct_fraud_transactions` | `velocity_1h_count` | `cbs_raw.transactions` | `txn_ref_no`, `acct_no`, `posting_datetime` | Count debit, non-reversal transactions in a rolling 1-hour window by `account_id`. | BRD 7.1.15 | Not null | Implemented in `int_txn_velocity`. |
| `fct_fraud_transactions` | `velocity_24h_amount_aud` | `cbs_raw.transactions` | `txn_amt`, `acct_no`, `posting_datetime` | Sum debit, non-reversal amounts in a rolling 24-hour window by `account_id`. | BRD 7.1.16 | Not null | Implemented in `int_txn_velocity`. |
| `fct_fraud_transactions` | `is_high_risk_mcc` | `ref.high_risk_mcc` | `merchant_category_code` | Left join to the reference set and flag matches as `TRUE`. | BRD 7.1.17 | Not null | Seed is intentionally empty until Fraud Operations provides the governed list. |
| `fct_fraud_transactions` | `pipeline_loaded_at` | System | - | Stamp `current_timestamp` at materialization. | BRD 7.1.18 | Not null | Supports audit trace requirements. |

## dim_customer_risk_profile

| Target Model | Target Column | Source Table | Source Column | Transformation Logic | Business Rule Reference | Data Quality Expectation | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `dim_customer_risk_profile` | `account_id` | `crm_raw.customers` | `acct_no` | Strip leading zeros with `ltrim`. | BRD 7.2.1 | Unique, not null | Model excludes only closed accounts in the current implementation. |
| `dim_customer_risk_profile` | `customer_id` | `crm_raw.customers` | `cust_id` | Pass through. | BRD 7.2.2 | Not null | One customer may appear on multiple accounts. |
| `dim_customer_risk_profile` | `customer_segment_code` | `crm_raw.customers` | `seg_cd` | Map `MASS/PREM/PRIV/BUS` to `MASS/PREMIUM/PRIVATE/BUSINESS`. | BRD 7.2.3 | Not null | Unexpected values default to `MASS` pending source governance. |
| `dim_customer_risk_profile` | `account_open_date` | `crm_raw.customers` | `acct_open_dt` | Parse `YYYYMMDD` text with `to_date`. | BRD 7.2.4 | Not null | |
| `dim_customer_risk_profile` | `account_tenure_days` | Derived | - | `current_date - account_open_date`. | BRD 7.2.5 | Not null | Postgres integer date arithmetic replaces Snowflake `DATEDIFF`. |
| `dim_customer_risk_profile` | `kyc_status` | `crm_raw.kyc_assessments` | `kyc_status_cd` | Choose latest assessment per `cust_id` and map `PASS/PEND/FAIL/EXP` to `VERIFIED/PENDING/FAILED/EXPIRED`. | BRD 7.2.6 | Not null | Defaults to `PENDING` where no KYC row exists. |
| `dim_customer_risk_profile` | `kyc_last_assessed_date` | `crm_raw.kyc_assessments` | `assessment_dt` | Take the latest assessment date per `cust_id`. | BRD 7.2.7 | Nullable | Implemented in `int_customer_latest_kyc`. |
| `dim_customer_risk_profile` | `pep_flag` | `crm_raw.kyc_assessments` | `pep_ind` | Map `1/0` to boolean from the latest KYC row. | BRD 7.2.8 | Not null | Defaults to `FALSE` where no KYC row exists. |
| `dim_customer_risk_profile` | `adverse_media_flag` | `crm_raw.kyc_assessments` | `adverse_media_ind` | Map `1/0` to boolean from the latest KYC row. | BRD 7.2.9 | Not null | Defaults to `FALSE` where no KYC row exists. |
| `dim_customer_risk_profile` | `lifetime_confirmed_fraud_count` | `acm_raw.fraud_cases` | `case_uuid`, `disposition_cd` | Count cases with mapped disposition `CONFIRMED` by `account_id`. | BRD 7.2.10 | Not null | Defaults to `0`. |
| `dim_customer_risk_profile` | `lifetime_confirmed_fraud_amount_aud` | `acm_raw.fraud_cases` | `case_loss_amt`, `disposition_cd` | Sum confirmed fraud case losses after dividing cents by `100.0`. | BRD 7.2.11 | Not null | Defaults to `0.00`. |
| `dim_customer_risk_profile` | `last_fraud_confirmed_date` | `acm_raw.fraud_cases` | `case_close_ts`, `disposition_cd` | Take the latest confirmed case close date by `account_id`. | BRD 7.2.12 | Nullable | |
| `dim_customer_risk_profile` | `avg_monthly_spend_aud_3m` | `cbs_raw.transactions` | `txn_amt`, `acct_no`, `posting_datetime` | Sum debit, non-reversal amounts over the last 90 days and divide by `3.0`. | BRD 7.2.13 | Nullable | Implemented in `int_txn_spend_baseline`. |
| `dim_customer_risk_profile` | `dominant_txn_country` | `cbs_raw.transactions` | `merch_country`, `acct_no`, `posting_datetime` | Pick the most common merchant country over the last 90 days per account. | BRD 7.2.14 | Nullable | Ties resolve alphabetically. |
| `dim_customer_risk_profile` | `risk_tier` | Derived | - | `HIGH` if `pep_flag` or confirmed fraud count > 0; `MEDIUM` if `kyc_status in ('PENDING','EXPIRED')`; else `LOW`. | BRD 7.2.15 | Not null; accepted values | `FAILED` currently falls through to `LOW` because the BRD does not define a separate rule. |
| `dim_customer_risk_profile` | `pipeline_loaded_at` | System | - | Stamp `current_timestamp` at materialization. | BRD 7.2.16 | Not null | Supports audit trace requirements. |

## fct_fraud_alerts

| Target Model | Target Column | Source Table | Source Column | Transformation Logic | Business Rule Reference | Data Quality Expectation | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `fct_fraud_alerts` | `alert_id` | `acm_raw.alerts` | `alert_uuid` | Rename to curated primary key. | BRD 7.3.1 | Unique, not null | |
| `fct_fraud_alerts` | `transaction_id` | `acm_raw.alerts` | `txn_ref_no` | Pass through as the transaction foreign key. | BRD 7.3.2 | Not null; relationship to `fct_fraud_transactions.transaction_id` | |
| `fct_fraud_alerts` | `account_id` | `acm_raw.alerts` | `acct_no` | Strip leading zeros with `ltrim`. | BRD 7.3.3 | Not null | |
| `fct_fraud_alerts` | `alert_generated_at` | `acm_raw.alerts` | `alert_ts` | Cast ISO 8601 AEST text to `timestamptz` and convert to UTC. | BRD 7.3.4 | Not null | |
| `fct_fraud_alerts` | `alert_rule_id` | `acm_raw.alerts` | `rule_cd` | Pass through. | BRD 7.3.5 | Not null | |
| `fct_fraud_alerts` | `alert_rule_description` | `acm_raw.alerts` | `rule_desc` | Pass through. | BRD 7.3.6 | Nullable | |
| `fct_fraud_alerts` | `alert_score` | `acm_raw.alerts` | `ml_score` | Divide by `10000.0` and clamp to `[0,1]`; preserve null for rule-only alerts. | BRD 7.3.7 | Nullable; range check `0..1` | |
| `fct_fraud_alerts` | `alert_priority` | Derived | - | `HIGH` if score >= `0.85` or rule in `RUL-007/RUL-011`; `MEDIUM` if score >= `0.60`; else `LOW`. | BRD 7.3.8 | Not null; accepted values | |
| `fct_fraud_alerts` | `case_id` | `acm_raw.fraud_cases` | `case_uuid` | Left join case on `alert_uuid`. | BRD 7.3.9 | Nullable | |
| `fct_fraud_alerts` | `case_opened_at` | `acm_raw.fraud_cases` | `case_open_ts` | Convert AEST text to UTC timestamp. | BRD 7.3.10 | Nullable | |
| `fct_fraud_alerts` | `case_closed_at` | `acm_raw.fraud_cases` | `case_close_ts` | Convert AEST text to UTC timestamp. | BRD 7.3.11 | Nullable | |
| `fct_fraud_alerts` | `disposition_code` | `acm_raw.fraud_cases` | `disposition_cd` | Map `CONF/DECL/PEND/ESCL` to `CONFIRMED/DECLINED/PENDING/ESCALATED`. | BRD 7.3.12 | Nullable; accepted values | |
| `fct_fraud_alerts` | `investigator_id` | `acm_raw.investigator_actions` | `investigator_emp_id` | Take the latest investigator action per `case_id`. | BRD 7.3.13 | Nullable | Implemented in `int_alert_case_actions`. |
| `fct_fraud_alerts` | `time_to_disposition_minutes` | Derived | - | Floor the minute difference between `case_closed_at` and `alert_generated_at`. | BRD 7.3.14 | Nullable | Null while the case remains open. |
| `fct_fraud_alerts` | `is_true_positive` | Derived | - | `disposition_code = 'CONFIRMED'`. | BRD 7.3.15 | Not null | Defaults to `FALSE`. |
| `fct_fraud_alerts` | `is_false_positive` | Derived | - | `disposition_code = 'DECLINED'`. | BRD 7.3.16 | Not null | Defaults to `FALSE`. |
| `fct_fraud_alerts` | `feedback_loop_eligible` | Derived | - | `disposition_code in ('CONFIRMED','DECLINED') and case_closed_at is not null`. | BRD 7.3.17 | Not null | |
| `fct_fraud_alerts` | `pipeline_loaded_at` | System | - | Stamp `current_timestamp` at materialization. | BRD 7.3.18 | Not null | Supports audit trace requirements. |
