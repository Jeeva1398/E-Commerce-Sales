"""Pull the mysql source tables into the raw schema in postgres.

Full refresh: truncate the landing table, reload everything. Fine at this volume;
the source tables carry updated_at so this can move to an incremental pull later.
"""

import csv
import io
import os
import sys
import time
from pathlib import Path

import psycopg2
import pymysql
import pymysql.cursors
from dotenv import load_dotenv

load_dotenv()

DDL = Path(__file__).with_name("raw_tables.sql")
CHUNK = 5000
NULL_MARKER = "\\N"

TABLES = {
    "categories": ["category_id", "name", "created_at"],
    "customers": [
        "customer_id", "first_name", "last_name", "email", "phone",
        "city", "state", "country", "signup_date", "created_at", "updated_at",
    ],
    "products": [
        "product_id", "category_id", "name", "sku", "price", "cost",
        "is_active", "created_at", "updated_at",
    ],
    "orders": [
        "order_id", "customer_id", "order_date", "status", "payment_method",
        "shipping_city", "shipping_country", "total_amount", "created_at", "updated_at",
    ],
    "order_items": [
        "order_item_id", "order_id", "product_id", "quantity", "unit_price",
        "discount", "line_total", "created_at",
    ],
}


def mysql_conn():
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", 3307)),
        user=os.getenv("MYSQL_USER", "ecom"),
        password=os.getenv("MYSQL_PASSWORD", "ecom"),
        database=os.getenv("MYSQL_DATABASE", "ecom"),
        cursorclass=pymysql.cursors.SSCursor,
    )


def pg_conn():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "127.0.0.1"),
        port=int(os.getenv("POSTGRES_PORT", 5433)),
        user=os.getenv("POSTGRES_USER", "warehouse"),
        password=os.getenv("POSTGRES_PASSWORD", "warehouse"),
        dbname=os.getenv("POSTGRES_DB", "warehouse"),
    )


def ensure_tables(pg):
    with pg.cursor() as cur:
        cur.execute(DDL.read_text())


def to_buffer(rows):
    buf = io.StringIO()
    w = csv.writer(buf)
    for row in rows:
        w.writerow([NULL_MARKER if v is None else v for v in row])
    buf.seek(0)
    return buf


def copy_table(my, pg, table, columns):
    cols = ", ".join(columns)
    with my.cursor() as src:
        src.execute(f"SELECT {cols} FROM {table}")

        with pg.cursor() as dest:
            dest.execute(f"TRUNCATE TABLE raw.{table}")

            n = 0
            while True:
                rows = src.fetchmany(CHUNK)
                if not rows:
                    break
                dest.copy_expert(
                    f"COPY raw.{table} ({cols}) FROM STDIN WITH (FORMAT csv, NULL '{NULL_MARKER}')",
                    to_buffer(rows),
                )
                n += len(rows)
    return n


def run():
    my = mysql_conn()
    pg = pg_conn()
    ensure_tables(pg)

    counts = {}
    for table, columns in TABLES.items():
        t0 = time.time()
        counts[table] = copy_table(my, pg, table, columns)
        print(f"{table:<12} {counts[table]:>7} rows  {time.time() - t0:.1f}s")

    pg.commit()
    pg.close()
    my.close()
    return counts


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        print(f"extraction failed: {e}", file=sys.stderr)
        raise
