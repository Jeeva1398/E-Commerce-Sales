"""Populate the MySQL source db with fake but plausible e-commerce data."""

import os
import random
from datetime import datetime, timedelta

import pymysql
from dotenv import load_dotenv
from faker import Faker

load_dotenv()

fake = Faker()
Faker.seed(42)
random.seed(42)

N_CUSTOMERS = int(os.getenv("SEED_CUSTOMERS", 2000))
N_PRODUCTS = int(os.getenv("SEED_PRODUCTS", 300))
N_ORDERS = int(os.getenv("SEED_ORDERS", 8000))

CATEGORIES = [
    "Electronics", "Home & Kitchen", "Books", "Clothing", "Sports & Outdoors",
    "Beauty", "Toys & Games", "Grocery", "Automotive", "Pet Supplies",
    "Office", "Garden",
]

STATUSES = ["pending", "paid", "shipped", "delivered", "cancelled", "returned"]
STATUS_WEIGHTS = [5, 12, 15, 58, 7, 3]
PAYMENTS = ["card", "upi", "netbanking", "wallet", "cod"]

START = datetime.now() - timedelta(days=730)


def connect():
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", 3307)),
        user=os.getenv("MYSQL_USER", "ecom"),
        password=os.getenv("MYSQL_PASSWORD", "ecom"),
        database=os.getenv("MYSQL_DATABASE", "ecom"),
        autocommit=False,
    )


def wipe(cur):
    cur.execute("SET FOREIGN_KEY_CHECKS = 0")
    for t in ("order_items", "orders", "products", "customers", "categories"):
        cur.execute(f"TRUNCATE TABLE {t}")
    cur.execute("SET FOREIGN_KEY_CHECKS = 1")


def load_categories(cur):
    rows = [(name,) for name in CATEGORIES]
    cur.executemany("INSERT INTO categories (name) VALUES (%s)", rows)
    cur.execute("SELECT category_id FROM categories")
    return [r[0] for r in cur.fetchall()]


def load_customers(cur):
    rows = []
    for _ in range(N_CUSTOMERS):
        first = fake.first_name()
        last = fake.last_name()
        # unique_id keeps the email unique without relying on faker's uniqueness pool
        email = f"{first}.{last}.{fake.unique.random_number(digits=6)}@{fake.free_email_domain()}".lower()
        rows.append((
            first,
            last,
            email,
            fake.msisdn()[:12],
            fake.city(),
            fake.state(),
            fake.country(),
            fake.date_between(start_date="-3y", end_date="today"),
        ))

    cur.executemany(
        """INSERT INTO customers
           (first_name, last_name, email, phone, city, state, country, signup_date)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
        rows,
    )
    cur.execute("SELECT customer_id, signup_date FROM customers")
    return cur.fetchall()


def load_products(cur, category_ids):
    rows = []
    for i in range(N_PRODUCTS):
        price = round(random.uniform(5, 900), 2)
        cost = round(price * random.uniform(0.45, 0.8), 2)
        rows.append((
            random.choice(category_ids),
            fake.catch_phrase(),
            f"SKU-{i + 1:05d}",
            price,
            cost,
            0 if random.random() < 0.08 else 1,
        ))

    cur.executemany(
        """INSERT INTO products (category_id, name, sku, price, cost, is_active)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        rows,
    )
    cur.execute("SELECT product_id, price FROM products")
    return cur.fetchall()


def load_orders(cur, customers, products):
    orders = []
    for _ in range(N_ORDERS):
        customer_id, signup = random.choice(customers)
        # an order can't predate the signup
        earliest = max(START.date(), signup)
        order_date = fake.date_time_between(start_date=earliest, end_date="now")
        orders.append((
            customer_id,
            order_date,
            random.choices(STATUSES, weights=STATUS_WEIGHTS)[0],
            random.choice(PAYMENTS),
            fake.city(),
            fake.country(),
        ))

    cur.executemany(
        """INSERT INTO orders
           (customer_id, order_date, status, payment_method, shipping_city, shipping_country)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        orders,
    )

    cur.execute("SELECT order_id FROM orders")
    order_ids = [r[0] for r in cur.fetchall()]

    items = []
    for order_id in order_ids:
        for product_id, price in random.sample(products, random.randint(1, 5)):
            qty = random.randint(1, 4)
            price = float(price)
            discount = round(price * qty * random.choice([0, 0, 0, 0.05, 0.1, 0.2]), 2)
            items.append((
                order_id,
                product_id,
                qty,
                price,
                discount,
                round(price * qty - discount, 2),
            ))

    cur.executemany(
        """INSERT INTO order_items
           (order_id, product_id, quantity, unit_price, discount, line_total)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        items,
    )

    cur.execute(
        """UPDATE orders o
           JOIN (SELECT order_id, SUM(line_total) AS total
                 FROM order_items GROUP BY order_id) i ON i.order_id = o.order_id
           SET o.total_amount = i.total"""
    )
    return len(order_ids), len(items)


def main():
    conn = connect()
    cur = conn.cursor()

    wipe(cur)
    category_ids = load_categories(cur)
    customers = load_customers(cur)
    products = load_products(cur, category_ids)
    n_orders, n_items = load_orders(cur, customers, products)
    conn.commit()

    print(f"categories {len(category_ids)}")
    print(f"customers  {len(customers)}")
    print(f"products   {len(products)}")
    print(f"orders     {n_orders}")
    print(f"items      {n_items}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
