"""Seed -> extract -> dbt -> metabase, checked end to end.

Seeds a deliberately odd number of orders and then asserts that exact number
comes back out of the metabase cards. Re-running the pipeline over unchanged
data would pass a weaker check even if a step silently did nothing.

    python scripts/e2e_test.py 1234
"""

import os
import subprocess
import sys
import time

sys.path.insert(0, "extraction")
sys.path.insert(0, "metabase")

import provision as mb
import pymysql.cursors
from extract_to_staging import mysql_conn, pg_conn

DAG = "ecom_pipeline"
SCHEDULER = "ecom-airflow-scheduler"
WAREHOUSE = "ecom-warehouse"

failures = []


def check(label, got, want):
    ok = got == want
    print(f"  [{'ok' if ok else 'FAIL'}] {label}: {got}" + ("" if ok else f" (expected {want})"))
    if not ok:
        failures.append(label)


def docker(*args, capture=True):
    return subprocess.run(["docker", *args], capture_output=capture, text=True)


def seed(n_orders):
    env = dict(os.environ, SEED_ORDERS=str(n_orders))
    r = subprocess.run([sys.executable, "mysql-source/seed.py"], env=env,
                       capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"seed failed:\n{r.stderr}")
    print(r.stdout.strip())


def wipe_warehouse():
    with pg_conn() as pg, pg.cursor() as cur:
        cur.execute("TRUNCATE raw.categories, raw.customers, raw.products, raw.orders, raw.order_items")
        for s in ("analytics_staging", "analytics_intermediate", "analytics_marts"):
            cur.execute(f"DROP SCHEMA IF EXISTS {s} CASCADE")
        pg.commit()


def run_dag(run_id):
    docker("exec", SCHEDULER, "airflow", "dags", "trigger", DAG, "-r", run_id)

    deadline = time.time() + 600
    while time.time() < deadline:
        time.sleep(10)
        out = docker("exec", SCHEDULER, "airflow", "tasks", "states-for-dag-run", DAG, run_id).stdout
        states = {}
        for line in out.splitlines():
            for task in ("extract_to_raw", "dbt_run", "dbt_test"):
                if task in line:
                    states[task] = line.rsplit("|")[-3].strip() if "|" in line else "?"
        done = [s for s in states.values() if s in ("success", "failed", "upstream_failed")]
        if len(done) == 3:
            return states
    return states


def source_counts():
    # extract_to_staging hands back a streaming cursor, which complains if you
    # run small lookups back to back on it
    with mysql_conn() as my, my.cursor(pymysql.cursors.Cursor) as cur:
        counts = {}
        for t in ("categories", "customers", "products", "orders", "order_items"):
            cur.execute(f"SELECT count(*) FROM {t}")
            counts[t] = cur.fetchone()[0]
        cur.execute("SELECT round(sum(total_amount)) FROM orders")
        counts["total"] = int(cur.fetchone()[0])
    return counts


def warehouse_counts():
    with pg_conn() as pg, pg.cursor() as cur:
        out = {}
        for t in ("categories", "customers", "products", "orders", "order_items"):
            cur.execute(f"SELECT count(*) FROM raw.{t}")
            out[f"raw_{t}"] = cur.fetchone()[0]
        cur.execute("SELECT count(*), count(DISTINCT order_id), round(sum(line_total)) FROM analytics_marts.fact_orders")
        out["fact_lines"], out["fact_orders"], total = cur.fetchone()
        out["fact_total"] = int(total)
        cur.execute("SELECT count(*) FROM analytics_marts.dim_customers")
        out["dim_customers"] = cur.fetchone()[0]
    return out


def metabase_totals():
    session = mb.api("POST", "/api/session", {"username": mb.EMAIL, "password": mb.PASSWORD})["id"]
    out = {}
    for card in mb.api("GET", "/api/card", session=session):
        res = mb.api("POST", f"/api/card/{card['id']}/query", session=session)
        if res["status"] != "completed":
            failures.append(f"card {card['name']} errored")
            continue
        out[card["name"]] = res["data"]["rows"]
    return out


def main():
    n_orders = int(sys.argv[1]) if len(sys.argv) > 1 else 1234

    print(f"\n== seeding {n_orders} orders ==")
    seed(n_orders)

    print("\n== wiping warehouse ==")
    wipe_warehouse()

    print(f"\n== running {DAG} ==")
    run_id = f"e2e_{int(time.time())}"
    states = run_dag(run_id)
    for task, state in states.items():
        check(f"task {task}", state, "success")

    src = source_counts()
    wh = warehouse_counts()
    mbt = metabase_totals()

    print("\n== raw mirrors the source ==")
    for t in ("categories", "customers", "products", "orders", "order_items"):
        check(f"raw.{t}", wh[f"raw_{t}"], src[t])

    print("\n== marts reconcile ==")
    check("fact line count", wh["fact_lines"], src["order_items"])
    check("distinct orders in fact", wh["fact_orders"], n_orders)
    check("dim_customers", wh["dim_customers"], src["customers"])
    check("sum(line_total) vs source", wh["fact_total"], src["total"])

    print("\n== metabase sees the new data ==")
    volume = mbt.get("Order volume by month", [])
    check("order volume card sums to seeded orders", sum(r[1] for r in volume), n_orders)
    check("top products card rows", len(mbt.get("Top 10 products by revenue", [])), 10)
    check("ltv card rows", len(mbt.get("Customer lifetime value", [])), 20)
    revenue = mbt.get("Revenue by month", [])
    check("revenue card has months", len(revenue) > 0, True)
    check("revenue card months match volume card", len(revenue), len(volume))

    print()
    if failures:
        print(f"FAILED ({len(failures)}): {', '.join(failures)}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
