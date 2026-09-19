select
    product_id,
    category_id,
    trim(name) as product_name,
    sku,
    price,
    cost,
    price - cost as unit_margin,
    is_active = 1 as is_active
from {{ source('raw', 'products') }}
