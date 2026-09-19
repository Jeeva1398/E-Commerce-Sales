select
    order_id,
    customer_id,
    order_date,
    order_date::date as order_day,
    status,
    payment_method,
    shipping_city,
    shipping_country,
    total_amount,
    -- cancelled and returned orders stay in the fact table but shouldn't count
    -- as revenue
    status not in ('cancelled', 'returned') as is_revenue
from {{ source('raw', 'orders') }}
