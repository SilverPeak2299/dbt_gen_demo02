{{ config(materialized='view') }}

with source as (

    select * from {{ source('cbs_raw', 'transactions') }}

),

ranked as (

    select
        *,
        row_number() over (
            partition by txn_ref_no
            order by load_timestamp desc
        ) as row_num
    from source

),

deduped as (

    select * from ranked where row_num = 1

)

select
    txn_ref_no as transaction_id_raw,
    posting_datetime::timestamptz at time zone 'UTC' as transaction_timestamp_utc,
    (posting_datetime::timestamptz at time zone 'UTC')::date as transaction_date_utc,
    nullif(ltrim(acct_no, '0'), '') as account_id,
    case txn_channel_cd
        when '01' then 'ATM'
        when '02' then 'POS'
        when '03' then 'CNP'
        when '04' then 'BRANCH'
        when '99' then 'OTHER'
        else 'OTHER'
    end as channel_code,
    (txn_amt::numeric / 100.0)::numeric(18, 2) as transaction_amount_aud,
    txn_dr_cr_ind as transaction_direction,
    coalesce(nullif(trim(mcc), ''), '0000') as merchant_category_code,
    nullif(trim(merchant_ref), '') as merchant_id,
    nullif(upper(trim(merch_country)), '') as merchant_country_code,
    coalesce(reversal_ind, 'N') = 'Y' as is_reversal,
    orig_txn_ref_no as original_transaction_id,
    load_timestamp as source_loaded_at
from deduped
