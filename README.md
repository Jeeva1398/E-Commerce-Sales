# E-Commerce Sales Data Pipeline

Batch ELT pipeline over a simulated e-commerce OLTP system: MySQL source -> Postgres warehouse
-> dbt star schema -> Metabase dashboards, orchestrated with Airflow. All local, via Docker Compose.

Build log / architecture notes: `Ecommerce-Data-Pipeline-Architecture-Context.md`

## Status

- [x] Phase 1 — project setup, MySQL source schema, Faker seed
- [ ] Phase 2 — extraction into the Postgres `raw` schema
- [ ] Phase 3 — Airflow DAG for the extraction
- [ ] Phase 4 — dbt models + tests
- [ ] Phase 5 — full pipeline in one DAG
- [ ] Phase 6 — Metabase dashboards
- [ ] Phase 7 — polish

## Stack

Python, MySQL 8 (source), Postgres 16 (warehouse), Airflow, dbt, Metabase, Docker Compose, Faker.

## Getting started

```bash
cp .env.example .env
docker compose up -d

python -m venv .venv
.venv\Scripts\activate        # source .venv/bin/activate on mac/linux
pip install -r requirements.txt

python mysql-source/seed.py
```

`schema.sql` runs automatically the first time the mysql container is created. If you change it
after that, you need `docker compose down -v` to get it re-applied.

The seed truncates everything first, so it's safe to re-run. Volumes default to 2000 customers /
300 products / 8000 orders and can be overridden with `SEED_CUSTOMERS`, `SEED_PRODUCTS`,
`SEED_ORDERS`.

Default ports are 3307 (mysql) and 5433 (postgres) to stay out of the way of anything already
running locally.

## Source schema

`categories`, `customers`, `products`, `orders`, `order_items` — normalised OLTP shape, FKs
enforced. `orders`/`order_items` are the transactional tables the warehouse fact table is built
from in Phase 4.
