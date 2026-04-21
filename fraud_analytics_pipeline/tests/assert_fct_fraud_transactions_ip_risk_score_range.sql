select *
from {{ ref('fct_fraud_transactions') }}
where ip_risk_score is not null
  and (ip_risk_score < 0 or ip_risk_score > 1)
