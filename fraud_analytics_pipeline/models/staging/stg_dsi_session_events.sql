{{ config(materialized='view') }}

with source as (

    select * from {{ source('dsi_raw', 'session_events') }}

),

ranked as (

    select
        *,
        row_number() over (
            partition by session_uuid
            order by load_timestamp desc
        ) as row_num
    from source

),

deduped as (

    select * from ranked where row_num = 1

)

select
    session_uuid as session_id,
    session_txn_ref as transaction_id_raw,
    session_start_ts,
    session_end_ts,
    device_fp as device_fingerprint_hash,
    coalesce(new_device_flag, 'N') = 'Y' as is_new_device,
    case
        when ip_risk_score_raw is null then null
        else greatest(0::numeric, least(1::numeric, ip_risk_score_raw::numeric / 10000.0))::numeric(5, 4)
    end as ip_risk_score,
    upper(nullif(trim(geo_country_code), '')) as geo_country_code,
    load_timestamp as source_loaded_at,
    row_number() over (
        partition by session_txn_ref
        order by session_start_ts asc nulls last, session_uuid asc
    ) as transaction_session_rank
from deduped
