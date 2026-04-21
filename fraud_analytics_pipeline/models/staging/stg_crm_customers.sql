{{ config(materialized='view') }}

with source as (

    select * from {{ source('crm_raw', 'customers') }}

),

ranked as (

    select
        *,
        row_number() over (
            partition by acct_no
            order by snapshot_dt desc, acct_open_dt desc
        ) as row_num
    from source

),

deduped as (

    select * from ranked where row_num = 1

)

select
    nullif(ltrim(acct_no, '0'), '') as account_id,
    cust_id as customer_id,
    to_date(acct_open_dt, 'YYYYMMDD') as account_open_date,
    acct_status_cd as account_status_code,
    case seg_cd
        when 'MASS' then 'MASS'
        when 'PREM' then 'PREMIUM'
        when 'PRIV' then 'PRIVATE'
        when 'BUS' then 'BUSINESS'
        else 'MASS'
    end as customer_segment_code,
    product_cd as product_code,
    branch_cd as branch_code,
    snapshot_dt as snapshot_date
from deduped
