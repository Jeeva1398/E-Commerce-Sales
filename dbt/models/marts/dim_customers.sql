select
    customer_id,
    full_name,
    first_name,
    last_name,
    email,
    city,
    state,
    country,
    signup_date,
    signup_month
from {{ ref('stg_customers') }}
