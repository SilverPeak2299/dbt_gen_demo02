{{ config(materialized='view') }}

select
    account_id,
    count(*) filter (
        where disposition_code = 'CONFIRMED'
    )::integer as lifetime_confirmed_fraud_count,
    coalesce(
        sum(
            case
                when disposition_code = 'CONFIRMED' then case_loss_amount_aud
                else 0::numeric
            end
        ),
        0::numeric
    )::numeric(18, 2) as lifetime_confirmed_fraud_amount_aud,
    max(
        case
            when disposition_code = 'CONFIRMED' then case_closed_at::date
            else null
        end
    ) as last_fraud_confirmed_date
from {{ ref('stg_acm_fraud_cases') }}
group by account_id
