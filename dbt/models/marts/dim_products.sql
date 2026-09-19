select
    p.product_id,
    p.product_name,
    p.sku,
    c.category_id,
    c.category_name,
    p.price,
    p.cost,
    p.unit_margin,
    p.is_active
from {{ ref('stg_products') }} p
join {{ ref('stg_categories') }} c on c.category_id = p.category_id
