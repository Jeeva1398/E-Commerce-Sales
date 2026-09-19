-- one row per order line, with the order and product context folded in so the
-- marts don't all have to repeat the same three joins
select
    i.order_item_id,
    i.order_id,
    i.product_id,
    o.customer_id,
    o.order_date,
    o.order_day,
    o.status,
    o.payment_method,
    o.is_revenue,
    p.category_id,
    i.quantity,
    i.unit_price,
    i.discount,
    i.line_total,
    p.cost * i.quantity as line_cost,
    i.line_total - (p.cost * i.quantity) as line_margin
from {{ ref('stg_order_items') }} i
join {{ ref('stg_orders') }} o on o.order_id = i.order_id
join {{ ref('stg_products') }} p on p.product_id = i.product_id
