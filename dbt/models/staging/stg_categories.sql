select
    category_id,
    trim(name) as category_name
from {{ source('raw', 'categories') }}
