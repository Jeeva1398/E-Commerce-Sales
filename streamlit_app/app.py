"""Public sales dashboard over the supabase marts.

Same four questions as the metabase dashboard (metabase/provision.py), since
metabase itself is too heavy for any free host. Reads analytics_marts only,
with a read-only login (scripts/supabase_readonly.sql).
"""

import pandas as pd
import psycopg2
import streamlit as st

st.set_page_config(page_title="E-commerce Sales", layout="wide")

QUERIES = {
    "kpis": """
        select
            sum(revenue) as revenue,
            count(distinct order_id) filter (where is_revenue) as orders,
            count(distinct customer_id) as customers,
            sum(revenue) / nullif(count(distinct order_id) filter (where is_revenue), 0) as aov
        from analytics_marts.fact_orders
    """,
    "revenue_by_month": """
        select d.month_start as month, sum(f.revenue) as revenue
        from analytics_marts.fact_orders f
        join analytics_marts.dim_date d on d.date_day = f.order_date
        group by 1
        order by 1
    """,
    "orders_by_month": """
        select d.month_start as month, count(distinct f.order_id) as orders
        from analytics_marts.fact_orders f
        join analytics_marts.dim_date d on d.date_day = f.order_date
        group by 1
        order by 1
    """,
    "top_products": """
        select p.product_name, sum(f.revenue) as revenue
        from analytics_marts.fact_orders f
        join analytics_marts.dim_products p on p.product_id = f.product_id
        group by 1
        order by revenue desc
        limit 10
    """,
    "customer_ltv": """
        select
            c.full_name,
            c.country,
            sum(f.revenue) as lifetime_value,
            count(distinct f.order_id) as orders
        from analytics_marts.fact_orders f
        join analytics_marts.dim_customers c on c.customer_id = f.customer_id
        group by 1, 2
        order by lifetime_value desc
        limit 20
    """,
}


# the pipeline runs once a day, so an hour of cache costs nothing and keeps
# the free-tier db from being hit on every page view
@st.cache_data(ttl=3600, show_spinner=False)
def load(name):
    cfg = st.secrets["warehouse"]
    with psycopg2.connect(
        host=cfg["host"],
        port=int(cfg.get("port", 5432)),
        user=cfg["user"],
        password=cfg["password"],
        dbname=cfg.get("dbname", "postgres"),
        sslmode="require",
    ) as conn:
        return pd.read_sql_query(QUERIES[name], conn)


st.title("E-commerce Sales")
st.caption("MySQL source → Supabase warehouse → dbt star schema. Refreshed daily by GitHub Actions.")

k = load("kpis").iloc[0]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Revenue", f"{k.revenue:,.0f}")
c2.metric("Orders", f"{int(k.orders):,}")
c3.metric("Customers", f"{int(k.customers):,}")
c4.metric("Avg order value", f"{k.aov:,.2f}")

left, right = st.columns(2)
with left:
    st.subheader("Revenue by month")
    st.line_chart(load("revenue_by_month"), x="month", y="revenue")
with right:
    st.subheader("Order volume by month")
    st.line_chart(load("orders_by_month"), x="month", y="orders")

left, right = st.columns(2)
with left:
    st.subheader("Top 10 products by revenue")
    top = load("top_products")
    st.bar_chart(top, x="product_name", y="revenue", horizontal=True, sort="-revenue")
with right:
    st.subheader("Customer lifetime value")
    st.dataframe(
        load("customer_ltv"),
        hide_index=True,
        width="stretch",
        column_config={
            "full_name": "Customer",
            "country": "Country",
            "lifetime_value": st.column_config.NumberColumn("Lifetime value", format="%.2f"),
            "orders": "Orders",
        },
    )
