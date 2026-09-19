-- grain: one row per order line. an order with three products is three rows,
-- so order-level counts need count(distinct order_id)
select
    order_item_id,
    order_id,
    customer_id,
    product_id,
    order_day as order_date,
    order_date as ordered_at,
    status,
    payment_method,
    is_revenue,
    quantity,
    unit_price,
    discount,
    line_total,
    line_cost,
    line_margin,
    case when is_revenue then line_total else 0 end as revenue
from {{ ref('int_order_lines') }}
