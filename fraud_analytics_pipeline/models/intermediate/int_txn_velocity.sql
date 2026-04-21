{{ config(materialized='view') }}

with base as (

    select
        transaction_id_raw,
        account_id,
        transaction_timestamp_utc,
        transaction_amount_aud
    from {{ ref('stg_cbs_transactions') }}
    where not is_reversal
      and transaction_direction = 'D'

),

windowed as (

    select
        transaction_id_raw,
        count(*) over (
            partition by account_id
            order by transaction_timestamp_utc
            range between interval '1 hour' preceding and current row
        )::integer as velocity_1h_count,
        sum(transaction_amount_aud) over (
            partition by account_id
            order by transaction_timestamp_utc
            range between interval '24 hours' preceding and current row
        )::numeric(18, 2) as velocity_24h_amount_aud
    from base

)

select * from windowed
