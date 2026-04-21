{{ config(materialized='view') }}

with base as (

    select
        account_id,
        transaction_amount_aud,
        merchant_country_code
    from {{ ref('stg_cbs_transactions') }}
    where not is_reversal
      and transaction_direction = 'D'
      and transaction_timestamp_utc >= current_timestamp - interval '90 days'

),

spend as (

    select
        account_id,
        round((sum(transaction_amount_aud) / 3.0)::numeric, 2) as avg_monthly_spend_aud_3m
    from base
    group by account_id

),

country_counts as (

    select
        account_id,
        merchant_country_code,
        count(*) as transaction_count
    from base
    where merchant_country_code is not null
    group by account_id, merchant_country_code

),

country_ranked as (

    select
        account_id,
        merchant_country_code,
        row_number() over (
            partition by account_id
            order by transaction_count desc, merchant_country_code asc
        ) as row_num
    from country_counts

)

select
    spend.account_id,
    spend.avg_monthly_spend_aud_3m,
    country_ranked.merchant_country_code as dominant_txn_country
from spend
left join country_ranked
    on spend.account_id = country_ranked.account_id
   and country_ranked.row_num = 1
