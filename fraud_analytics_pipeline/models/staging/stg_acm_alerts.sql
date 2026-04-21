{{ config(materialized='view') }}

with source as (

    select * from {{ source('acm_raw', 'alerts') }}

),

ranked as (

    select
        *,
        row_number() over (
            partition by alert_uuid
            order by load_timestamp desc
        ) as row_num
    from source

),

deduped as (

    select * from ranked where row_num = 1

)

select
    alert_uuid as alert_id,
    txn_ref_no as transaction_id_raw,
    nullif(ltrim(acct_no, '0'), '') as account_id,
    alert_ts::timestamptz at time zone 'UTC' as alert_generated_at,
    rule_cd as alert_rule_id,
    rule_desc as alert_rule_description,
    case
        when ml_score is null then null
        else greatest(0::numeric, least(1::numeric, ml_score::numeric / 10000.0))::numeric(5, 4)
    end as alert_score,
    alert_status_cd as alert_status_code,
    load_timestamp as source_loaded_at
from deduped
