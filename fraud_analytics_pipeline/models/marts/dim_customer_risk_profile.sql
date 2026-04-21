{{ config(materialized='table') }}

with customer_base as (

    select *
    from {{ ref('stg_crm_customers') }}
    where account_status_code <> 'C'

),

final as (

    select
        customers.account_id,
        customers.customer_id,
        customers.customer_segment_code,
        customers.account_open_date,
        (current_date - customers.account_open_date)::integer as account_tenure_days,
        coalesce(kyc.kyc_status, 'PENDING') as kyc_status,
        kyc.kyc_last_assessed_date,
        coalesce(kyc.pep_flag, false) as pep_flag,
        coalesce(kyc.adverse_media_flag, false) as adverse_media_flag,
        coalesce(exposure.lifetime_confirmed_fraud_count, 0) as lifetime_confirmed_fraud_count,
        coalesce(exposure.lifetime_confirmed_fraud_amount_aud, 0::numeric)::numeric(18, 2) as lifetime_confirmed_fraud_amount_aud,
        exposure.last_fraud_confirmed_date,
        baseline.avg_monthly_spend_aud_3m,
        baseline.dominant_txn_country,
        case
            when coalesce(kyc.pep_flag, false)
              or coalesce(exposure.lifetime_confirmed_fraud_count, 0) > 0 then 'HIGH'
            when coalesce(kyc.kyc_status, 'PENDING') in ('PENDING', 'EXPIRED') then 'MEDIUM'
            else 'LOW'
        end as risk_tier,
        current_timestamp as pipeline_loaded_at
    from customer_base as customers
    left join {{ ref('int_customer_latest_kyc') }} as kyc
        on customers.customer_id = kyc.customer_id
    left join {{ ref('int_customer_fraud_exposure') }} as exposure
        on customers.account_id = exposure.account_id
    left join {{ ref('int_txn_spend_baseline') }} as baseline
        on customers.account_id = baseline.account_id

)

select * from final
