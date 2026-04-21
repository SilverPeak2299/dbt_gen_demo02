{{ config(
    materialized='incremental',
    unique_key='transaction_id',
    incremental_strategy='delete+insert',
    on_schema_change='sync_all_columns'
) }}

with base_transactions as (

    select *
    from {{ ref('stg_cbs_transactions') }}
    where not is_reversal
      and transaction_direction = 'D'

),

first_session_per_transaction as (

    select *
    from {{ ref('stg_dsi_session_events') }}
    where transaction_session_rank = 1

),

high_risk_mcc as (

    select merchant_category_code
    from {{ ref('high_risk_mcc') }}

),

final as (

    select
        tx.transaction_id_raw as transaction_id,
        tx.transaction_timestamp_utc,
        tx.transaction_date_utc as transaction_date,
        tx.account_id,
        tx.channel_code,
        tx.transaction_amount_aud,
        tx.merchant_category_code,
        tx.merchant_id,
        tx.merchant_country_code,
        (tx.merchant_country_code is not null and tx.merchant_country_code <> 'AUS') as is_international,
        session.session_id,
        session.device_fingerprint_hash,
        session.ip_risk_score,
        coalesce(session.is_new_device, false) as is_new_device,
        coalesce(velocity.velocity_1h_count, 1) as velocity_1h_count,
        coalesce(velocity.velocity_24h_amount_aud, tx.transaction_amount_aud) as velocity_24h_amount_aud,
        (high_risk_mcc.merchant_category_code is not null) as is_high_risk_mcc,
        current_timestamp as pipeline_loaded_at
    from base_transactions as tx
    left join first_session_per_transaction as session
        on tx.transaction_id_raw = session.transaction_id_raw
    left join {{ ref('int_txn_velocity') }} as velocity
        on tx.transaction_id_raw = velocity.transaction_id_raw
    left join high_risk_mcc
        on tx.merchant_category_code = high_risk_mcc.merchant_category_code

)

select * from final
