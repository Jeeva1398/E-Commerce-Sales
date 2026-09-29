"""Point Metabase at the warehouse and build the sales dashboard.

Clicking through the setup wizard works fine, but then the dashboards only
exist in whoever's container ran it. This does the same thing repeatably.
"""

import json
import os
import urllib.error
import urllib.request

from dotenv import load_dotenv

load_dotenv()

BASE = os.getenv("METABASE_URL", "http://localhost:3000")
EMAIL = os.getenv("METABASE_ADMIN_EMAIL", "admin@example.com")
PASSWORD = os.getenv("METABASE_ADMIN_PASSWORD", "Ecom!Analytics2026")
DB_NAME = "ecom warehouse"
DASHBOARD = "E-commerce Sales"

CARDS = [
    {
        "name": "Revenue by month",
        "display": "line",
        "sql": """
            select d.month_start as month, sum(f.revenue) as revenue
            from analytics_marts.fact_orders f
            join analytics_marts.dim_date d on d.date_day = f.order_date
            group by 1
            order by 1
        """,
        "pos": (0, 0, 12, 6),
    },
    {
        "name": "Order volume by month",
        "display": "line",
        "sql": """
            select d.month_start as month, count(distinct f.order_id) as orders
            from analytics_marts.fact_orders f
            join analytics_marts.dim_date d on d.date_day = f.order_date
            group by 1
            order by 1
        """,
        "pos": (0, 12, 12, 6),
    },
    {
        "name": "Top 10 products by revenue",
        "display": "bar",
        "sql": """
            select p.product_name, sum(f.revenue) as revenue
            from analytics_marts.fact_orders f
            join analytics_marts.dim_products p on p.product_id = f.product_id
            group by 1
            order by revenue desc
            limit 10
        """,
        "pos": (6, 0, 12, 7),
    },
    {
        "name": "Customer lifetime value",
        "display": "table",
        "sql": """
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
        "pos": (6, 12, 12, 7),
    },
]


def api(method, path, payload=None, session=None):
    req = urllib.request.Request(f"{BASE}{path}", method=method)
    req.add_header("Content-Type", "application/json")
    if session:
        req.add_header("X-Metabase-Session", session)
    body = json.dumps(payload).encode() if payload is not None else None
    try:
        with urllib.request.urlopen(req, body) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method} {path} -> {e.code}: {e.read().decode()[:400]}") from None


def sign_in():
    props = api("GET", "/api/session/properties")
    if props["has-user-setup"]:
        return api("POST", "/api/session", {"username": EMAIL, "password": PASSWORD})["id"]

    return api("POST", "/api/setup", {
        "token": props["setup-token"],
        "user": {
            "first_name": "Admin",
            "last_name": "User",
            "email": EMAIL,
            "password": PASSWORD,
            "site_name": "Ecom Analytics",
        },
        "prefs": {"site_name": "Ecom Analytics", "allow_tracking": False},
    })["id"]


def ensure_database(session):
    for db in api("GET", "/api/database", session=session)["data"]:
        if db["name"] == DB_NAME:
            return db["id"]
        if db["name"] == "Sample Database":
            api("DELETE", f"/api/database/{db['id']}", session=session)

    # metabase used to accept a database block in /api/setup and no longer
    # does, so it gets added separately
    made = api("POST", "/api/database", {
        "engine": "postgres",
        "name": DB_NAME,
        "details": {
            "host": os.getenv("WAREHOUSE_HOST", "postgres"),
            "port": int(os.getenv("WAREHOUSE_PORT", 5432)),
            "dbname": os.getenv("POSTGRES_DB", "warehouse"),
            "user": os.getenv("POSTGRES_USER", "warehouse"),
            "password": os.getenv("POSTGRES_PASSWORD", "warehouse"),
            "ssl": False,
            # only the marts are worth exposing, raw and staging are noise
            "schema-filters-type": "inclusion",
            "schema-filters-patterns": "analytics_marts",
        },
    }, session=session)
    api("POST", f"/api/database/{made['id']}/sync_schema", session=session)
    return made["id"]


def upsert_cards(session, db_id):
    existing = {c["name"]: c["id"] for c in api("GET", "/api/card", session=session)}
    out = []
    for card in CARDS:
        if card["name"] in existing:
            out.append((existing[card["name"]], card))
            continue
        made = api("POST", "/api/card", {
            "name": card["name"],
            "display": card["display"],
            "dataset_query": {
                "type": "native",
                "database": db_id,
                "native": {"query": " ".join(card["sql"].split())},
            },
            "visualization_settings": {},
        }, session=session)
        out.append((made["id"], card))
    return out


def build_dashboard(session, cards):
    for d in api("GET", "/api/dashboard", session=session):
        if d["name"] == DASHBOARD:
            dash = api("GET", f"/api/dashboard/{d['id']}", session=session)
            break
    else:
        dash = api("POST", "/api/dashboard", {
            "name": DASHBOARD,
            "description": "revenue, volume, products and customer value off the marts",
        }, session=session)

    if dash.get("dashcards"):
        return dash["id"], False

    dashcards = []
    for i, (card_id, card) in enumerate(cards):
        row, col, size_x, size_y = card["pos"]
        dashcards.append({
            "id": -(i + 1),
            "card_id": card_id,
            "row": row,
            "col": col,
            "size_x": size_x,
            "size_y": size_y,
            "parameter_mappings": [],
            "visualization_settings": {},
        })

    api("PUT", f"/api/dashboard/{dash['id']}", {"dashcards": dashcards}, session=session)
    return dash["id"], True


def main():
    session = sign_in()
    db_id = ensure_database(session)
    cards = upsert_cards(session, db_id)
    dash_id, created = build_dashboard(session, cards)

    print(f"warehouse db id {db_id}")
    for card_id, card in cards:
        print(f"  card {card_id:>3}  {card['name']}")
    print(f"dashboard {'built' if created else 'already had cards'}: {BASE}/dashboard/{dash_id}")


if __name__ == "__main__":
    main()
