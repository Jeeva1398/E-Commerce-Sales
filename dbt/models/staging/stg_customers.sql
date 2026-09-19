select
    customer_id,
    trim(first_name) as first_name,
    trim(last_name) as last_name,
    trim(first_name) || ' ' || trim(last_name) as full_name,
    lower(email) as email,
    phone,
    city,
    state,
    country,
    signup_date,
    date_trunc('month', signup_date)::date as signup_month
from {{ source('raw', 'customers') }}
