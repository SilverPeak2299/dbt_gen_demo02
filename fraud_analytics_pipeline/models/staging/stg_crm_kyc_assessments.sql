{{ config(materialized='view') }}

with source as (

    select * from {{ source('crm_raw', 'kyc_assessments') }}

),

ranked as (

    select
        *,
        row_number() over (
            partition by assessment_id
            order by assessment_dt desc
        ) as row_num
    from source

),

deduped as (

    select * from ranked where row_num = 1

)

select
    assessment_id,
    cust_id as customer_id,
    assessment_dt as assessment_date,
    case kyc_status_cd
        when 'PASS' then 'VERIFIED'
        when 'PEND' then 'PENDING'
        when 'FAIL' then 'FAILED'
        when 'EXP' then 'EXPIRED'
        else 'FAILED'
    end as kyc_status,
    coalesce(pep_ind, '0') = '1' as pep_flag,
    coalesce(adverse_media_ind, '0') = '1' as adverse_media_flag,
    sanction_screen_dt as sanction_screen_date,
    analyst_id
from deduped
