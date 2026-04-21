{{ config(materialized='view') }}

with source as (

    select * from {{ source('acm_raw', 'fraud_cases') }}

),

ranked as (

    select
        *,
        row_number() over (
            partition by case_uuid
            order by load_timestamp desc
        ) as row_num
    from source

),

deduped as (

    select * from ranked where row_num = 1

)

select
    case_uuid as case_id,
    alert_uuid as alert_id,
    nullif(ltrim(acct_no, '0'), '') as account_id,
    case_open_ts::timestamptz at time zone 'UTC' as case_opened_at,
    case
        when case_close_ts is null then null
        else case_close_ts::timestamptz at time zone 'UTC'
    end as case_closed_at,
    case disposition_cd
        when 'CONF' then 'CONFIRMED'
        when 'DECL' then 'DECLINED'
        when 'PEND' then 'PENDING'
        when 'ESCL' then 'ESCALATED'
        else null
    end as disposition_code,
    case
        when case_loss_amt is null then null
        else (case_loss_amt::numeric / 100.0)::numeric(18, 2)
    end as case_loss_amount_aud,
    fraud_type_cd as fraud_type_code,
    load_timestamp as source_loaded_at
from deduped
