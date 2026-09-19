CREATE SCHEMA IF NOT EXISTS raw;

-- landing tables mirror the mysql source. types are deliberately loose here,
-- casting/cleanup is dbt's job in phase 4.

CREATE TABLE IF NOT EXISTS raw.categories (
    category_id INTEGER,
    name TEXT,
    created_at TIMESTAMP,
    _extracted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS raw.customers (
    customer_id INTEGER,
    first_name TEXT,
    last_name TEXT,
    email TEXT,
    phone TEXT,
    city TEXT,
    state TEXT,
    country TEXT,
    signup_date DATE,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    _extracted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS raw.products (
    product_id INTEGER,
    category_id INTEGER,
    name TEXT,
    sku TEXT,
    price NUMERIC(10,2),
    cost NUMERIC(10,2),
    is_active SMALLINT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    _extracted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS raw.orders (
    order_id INTEGER,
    customer_id INTEGER,
    order_date TIMESTAMP,
    status TEXT,
    payment_method TEXT,
    shipping_city TEXT,
    shipping_country TEXT,
    total_amount NUMERIC(12,2),
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    _extracted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS raw.order_items (
    order_item_id INTEGER,
    order_id INTEGER,
    product_id INTEGER,
    quantity INTEGER,
    unit_price NUMERIC(10,2),
    discount NUMERIC(10,2),
    line_total NUMERIC(12,2),
    created_at TIMESTAMP,
    _extracted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
