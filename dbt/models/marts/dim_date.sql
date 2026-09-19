-- generated from the order date range, padded out to whole years so joins
-- don't fall off the end when new data lands
with bounds as (
    select
        date_trunc('year', min(order_day))::date as start_day,
        (date_trunc('year', max(order_day)) + interval '1 year - 1 day')::date as end_day
    from {{ ref('stg_orders') }}
),

days as (
    select generate_series(start_day, end_day, interval '1 day')::date as date_day
    from bounds
)

select
    date_day,
    extract(year from date_day)::int as year,
    extract(quarter from date_day)::int as quarter,
    extract(month from date_day)::int as month,
    to_char(date_day, 'Mon') as month_name,
    date_trunc('month', date_day)::date as month_start,
    extract(day from date_day)::int as day_of_month,
    extract(isodow from date_day)::int as day_of_week,
    to_char(date_day, 'Dy') as day_name,
    extract(isodow from date_day) in (6, 7) as is_weekend
from days
