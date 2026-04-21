select *
from {{ ref('fct_fraud_transactions') }}
where transaction_amount_aud <= 0
