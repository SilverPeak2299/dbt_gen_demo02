{{ config(materialized='view') }}

with source as (

    select * from {{ source('acm_raw', 'investigator_actions') }}

),

ranked as (

    select
        *,
        row_number() over (
            partition by action_id
            order by load_timestamp desc
        ) as row_num
    from source

),

deduped as (

    select * from ranked where row_num = 1

)

select
    action_id,
    case_uuid as case_id,
    investigator_emp_id as investigator_id,
    action_ts as action_timestamp,
    action_type_cd as action_type_code,
    action_notes,
    load_timestamp as source_loaded_at
from deduped
