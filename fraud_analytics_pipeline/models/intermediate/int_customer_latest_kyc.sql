{{ config(materialized='view') }}

with ranked as (

    select
        *,
        row_number() over (
            partition by customer_id
            order by assessment_date desc, assessment_id desc
        ) as row_num
    from {{ ref('stg_crm_kyc_assessments') }}

)

select
    customer_id,
    kyc_status,
    assessment_date as kyc_last_assessed_date,
    pep_flag,
    adverse_media_flag,
    sanction_screen_date
from ranked
where row_num = 1
