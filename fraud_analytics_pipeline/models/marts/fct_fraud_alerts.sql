{{ config(
    materialized='incremental',
    unique_key='alert_id',
    incremental_strategy='delete+insert',
    on_schema_change='sync_all_columns'
) }}

with base_alerts as (

    select *
    from {{ ref('stg_acm_alerts') }}

),

final as (

    select
        alerts.alert_id,
        alerts.transaction_id_raw as transaction_id,
        alerts.account_id,
        alerts.alert_generated_at,
        alerts.alert_rule_id,
        alerts.alert_rule_description,
        alerts.alert_score,
        case
            when coalesce(alerts.alert_score, 0) >= 0.85
              or alerts.alert_rule_id in ('RUL-007', 'RUL-011') then 'HIGH'
            when coalesce(alerts.alert_score, 0) >= 0.60 then 'MEDIUM'
            else 'LOW'
        end as alert_priority,
        case_actions.case_id,
        case_actions.case_opened_at,
        case_actions.case_closed_at,
        case_actions.disposition_code,
        case_actions.investigator_id,
        case
            when case_actions.case_closed_at is null then null
            else floor(extract(epoch from (case_actions.case_closed_at - alerts.alert_generated_at)) / 60)::integer
        end as time_to_disposition_minutes,
        coalesce(case_actions.disposition_code = 'CONFIRMED', false) as is_true_positive,
        coalesce(case_actions.disposition_code = 'DECLINED', false) as is_false_positive,
        (
            case_actions.disposition_code in ('CONFIRMED', 'DECLINED')
            and case_actions.case_closed_at is not null
        ) as feedback_loop_eligible,
        current_timestamp as pipeline_loaded_at
    from base_alerts as alerts
    left join {{ ref('int_alert_case_actions') }} as case_actions
        on alerts.alert_id = case_actions.alert_id

)

select * from final
