{{ config(materialized='view') }}

with latest_action as (

    select
        case_id,
        investigator_id
    from (
        select
            case_id,
            investigator_id,
            action_timestamp,
            action_id,
            row_number() over (
                partition by case_id
                order by action_timestamp desc nulls last, action_id desc
            ) as row_num
        from {{ ref('stg_acm_investigator_actions') }}
    ) ranked
    where row_num = 1

)

select
    cases.alert_id,
    cases.case_id,
    cases.account_id,
    cases.case_opened_at,
    cases.case_closed_at,
    cases.disposition_code,
    cases.case_loss_amount_aud,
    cases.fraud_type_code,
    latest_action.investigator_id
from {{ ref('stg_acm_fraud_cases') }} as cases
left join latest_action
    on cases.case_id = latest_action.case_id
