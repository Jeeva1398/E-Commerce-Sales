# E-Commerce Sales Data Pipeline

Batch ELT pipeline over a simulated e-commerce OLTP system: MySQL source -> Postgres warehouse
-> dbt star schema -> Metabase dashboards, orchestrated with Airflow. All local, via Docker Compose.

Build log / architecture notes: `Ecommerce-Data-Pipeline-Architecture-Context.md`

## Status

- [x] Phase 1 — project setup, MySQL source schema, Faker seed
- [x] Phase 2 — extraction into the Postgres `raw` schema
- [x] Phase 3 — Airflow DAG for the extraction
- [x] Phase 4 — dbt models + tests
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

## Extraction

```bash
python extraction/extract_to_staging.py
```

Reads the five source tables over a streaming cursor and `COPY`s them into `raw.*` in Postgres.
Full refresh — each landing table is truncated and reloaded, and the whole run is one transaction,
so a failure halfway through leaves the previous load intact. Rows get an `_extracted_at` stamp.

`raw_tables.sql` is idempotent and applied by the script itself, so there's nothing to run by hand
before the first extraction.

Full refresh is the deliberate starting point: the source is small, and it keeps the first Airflow
DAG simple. `orders`/`products`/`customers` carry `updated_at`, so switching to an incremental pull
is a change to this script and not to the schema.

## Orchestration

Airflow runs on the same compose stack (LocalExecutor, its own Postgres for metadata — kept
separate from the warehouse so a `dbt`-shaped mistake can't touch Airflow's own state).

```bash
docker compose up -d
```

UI at http://localhost:8080, login `admin` / `admin` (`AIRFLOW_ADMIN_PASSWORD` in `.env`).

One DAG, `ecom_extract`: a single `extract_to_raw` task calling the Phase 2 extraction, daily at
03:00, `catchup=False`, `max_active_runs=1`. Two retries five minutes apart. The task returns the
per-table row counts so they show up in XCom as well as the log.

The DAG imports `extraction.extract_to_staging` directly rather than shelling out — the
`extraction/` folder is mounted into the image and `PYTHONPATH` points at `/opt/airflow`, so the
same code runs by hand and under Airflow. Inside the network it reaches the databases by service
name on their internal ports, not the published 3307/5433.

Failures are logged from both `on_failure_callback` and `on_retry_callback`; the failure-only
callback doesn't fire until retries are exhausted, so on its own it would miss every intermediate
attempt.

## Transformation

```bash
docker compose run --rm dbt build      # or: dbt run / dbt test
```

dbt runs from the same image as Airflow but out of its own venv at
`/home/airflow/dbt-venv` — dbt and Airflow pin incompatible versions of jinja2 and friends, and
installing them side by side breaks one of them. The venv keeps both happy and means Phase 5 can
call dbt without a second image.

Layers, following the dbt convention:

| Layer | Schema | Materialised as | What it does |
|---|---|---|---|
| staging | `analytics_staging` | views | one model per source table — trim, cast, rename, derive `is_revenue` |
| intermediate | `analytics_intermediate` | view | `int_order_lines` joins items to their order and product once |
| marts | `analytics_marts` | tables | the star schema |

`fact_orders` is at **order-line grain** — one row per `order_item`, not per order. That's what
lets `dim_products` join to it at all; the price of it is that order-level counts need
`count(distinct order_id)`. `dim_date` is generated from the order range with `generate_series`
and padded out to whole years, so no package dependency and no gaps when new data arrives.

43 tests: unique/not-null on every key, referential integrity from the fact to all three dims and
across the staging layer, and `accepted_values` on order status. `dbt build` runs models and tests
together in dependency order — 53 nodes, clean.

The fact reconciles exactly to the source: 8000 distinct orders, 24061 lines, and
`sum(line_total)` matches `sum(total_amount)` on `raw.orders` to the rupee.
