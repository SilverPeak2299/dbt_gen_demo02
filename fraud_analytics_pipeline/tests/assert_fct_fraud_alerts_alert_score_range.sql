select *
from {{ ref('fct_fraud_alerts') }}
where alert_score is not null
  and (alert_score < 0 or alert_score > 1)
