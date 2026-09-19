# E-commerce Sales Data Pipeline — Architecture & Context

_Reference doc for building this project in phases — reviewed and committed by you after each phase, same workflow as ZenithDesk._

> Working name used in this doc: **ecom-data-pipeline**. Rename freely once you pick something.

---

## 1. Goal

A batch ELT pipeline that simulates a real e-commerce OLTP system, extracts data on a schedule, transforms it into a proper analytics warehouse (star schema), and surfaces it in a dashboard. Built to demonstrate core data engineering fundamentals for a job transition: extraction, orchestration, transformation, modeling, testing, and BI.

---

## 2. Tech Stack

| Layer | Choice |
|---|---|
| Language | Python |
| Source DB (OLTP) | MySQL |
| Warehouse (OLAP) | Postgres (local, Docker) |
| Orchestration | Airflow |
| Transformation | dbt |
| BI | Metabase |
| Environment | Docker Compose |
| Seed data | Faker (Python) |

---

## 3. Repo Structure (rough)

```
ecom-data-pipeline/
├── docker-compose.yml
├── mysql-source/
│   ├── schema.sql
│   └── seed.py
├── extraction/
│   └── extract_to_staging.py
├── airflow/
│   └── dags/
│       └── ecom_pipeline_dag.py
├── dbt/
│   ├── models/
│   │   ├── staging/
│   │   ├── intermediate/
│   │   └── marts/
│   └── dbt_project.yml
├── metabase/ (or just Docker service, no custom code)
└── README.md
```

---

## 4. Phases

### Phase 1 — Project setup & source data
- Repo init, Python env (`venv`/`poetry`), `.gitignore`
- `docker-compose.yml` with two services: `mysql` (source) + `postgres` (warehouse)
- OLTP schema in MySQL: `customers`, `products`, `categories`, `orders`, `order_items`
- Seed script using Faker — realistic-ish volumes (thousands of orders, not 10)
- **Deliverable**: `docker-compose up` gives you a populated MySQL instance

### Phase 2 — Extraction (E)
- Python script(s) pulling from MySQL, landing raw data into a `raw` schema in Postgres
- Start with full-refresh extraction (truncate + reload); note incremental as a future improvement
- **Deliverable**: raw tables in Postgres mirror MySQL source, runnable via `python extract_to_staging.py`

### Phase 3 — Orchestration (first pass)
- Airflow via Docker Compose (`apache/airflow` image)
- One DAG: schedule the Phase 2 extraction, basic retry policy, failure logging
- **Deliverable**: DAG visible and runnable in the Airflow UI

### Phase 4 — Transformation (dbt)
- dbt project pointed at the Postgres warehouse
- staging models → intermediate models → mart models
- Star schema: `fact_orders`, `dim_customers`, `dim_products`, `dim_date`
- dbt tests: not-null, unique, relationships (referential integrity between fact and dims)
- **Deliverable**: `dbt run && dbt test` passes clean

### Phase 5 — Full pipeline orchestration
- Extend the DAG: extract → `dbt run` → `dbt test`, one scheduled pipeline
- Failure alerting/logging across all three steps
- **Deliverable**: one Airflow DAG run takes raw MySQL data all the way to tested mart tables

### Phase 6 — BI layer
- Metabase (Dockerized) connected to the mart tables
- A handful of real dashboards: revenue by month, top products, customer LTV, order volume trend
- **Deliverable**: shareable dashboard screenshots for the portfolio

### Phase 7 — Portfolio polish
- README: architecture diagram, data lineage, design-decision writeup (why star schema, why full-refresh first, what you'd change for production scale)
- Clean up any leftover debug code, `.env.example` instead of committed secrets
- **Deliverable**: repo is presentable to a recruiter/interviewer cold

---

## 5. Writing code and commits that read as your own

The point of this section: AI-generated code and commits have a recognizable "signature" — overly uniform structure, exhaustive comments, textbook-perfect error handling everywhere, boilerplate commit messages. Reviewing and lightly reworking before committing (which is already your workflow) is what actually fixes this — these are the specific things to look for and adjust.

**Code smells to fix before committing:**
- Comments explaining *what* the code does line-by-line (obvious from reading it) — cut these. Keep only comments that explain *why* a non-obvious choice was made.
- Every function wrapped in exhaustive try/catch with perfectly worded error messages — real code has uneven error handling; some scripts fail loudly and get fixed later, not every path is defensively coded on day one.
- Uniform docstrings on every single function, including trivial ones — only document what actually needs it.
- Unnaturally consistent formatting/spacing across every file — a little inconsistency (spacing, quote style variance between files written at different times) is normal for a solo project built over weeks.
- Variable/function names that are overly descriptive or generic-textbook (`process_customer_data_and_return_result`) — shorten to what you'd actually type (`load_customers`).
- No dead code, no leftover debug prints, no commented-out old attempts — real WIP repos have some of this; you don't need to scrub every trace, just don't leave it *pristine*.

**Commit habits that read as human:**
- Multiple small commits per phase, not one giant "Phase 3 complete" commit — e.g. "add mysql schema", "seed customers and orders", "fix faker date range bug"
- Short, lowercase, imperative messages — `fix retry logic in extraction dag`, not `feat: implement comprehensive retry mechanism for extraction DAG with exponential backoff`
- Occasional fixup commits (`fix typo`, `oops, wrong env var`) — nobody's git history is perfectly linear
- Commit messages don't need a body/bullet list for routine changes — save detailed messages for genuinely significant decisions
- Some commits made at odd hours / in bursts, not perfectly evenly spaced — natural if you're doing this around a day job

**Bottom line:** since you already review and commit everything yourself rather than having it auto-committed, the fix is in the review pass — trim the comments, loosen the formatting, write the commit message the way you'd actually phrase it, not the way it was generated.

---

## 6. Open decisions to make as you go
- Incremental vs full-refresh extraction (start full, revisit in Phase 2/5)
- Airflow scheduling cadence (daily is standard for a portfolio project)
- Whether to add Great Expectations for data quality checks beyond dbt tests (optional, Phase 4/7 stretch)
- Whether to eventually port the warehouse to a cloud free tier (Snowflake/BigQuery) as a follow-up, once local version is solid
