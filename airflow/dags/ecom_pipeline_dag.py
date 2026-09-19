import logging
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

from extraction.extract_to_staging import run

log = logging.getLogger(__name__)

DBT = "/home/airflow/dbt-venv/bin/dbt"
DBT_DIR = "/opt/airflow/dbt"


def log_failure(context):
    ti = context["task_instance"]
    log.error(
        "pipeline step failed: task=%s run=%s attempt=%s/%s",
        ti.task_id,
        context["run_id"],
        ti.try_number,
        # max_tries drifts upward every time a task is cleared, so report the
        # configured limit instead
        ti.task.retries + 1,
    )


default_args = {
    "owner": "jeeva",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    # on_failure_callback only fires once retries are exhausted, so log the
    # intermediate attempts too
    "on_failure_callback": log_failure,
    "on_retry_callback": log_failure,
}

with DAG(
    dag_id="ecom_pipeline",
    description="mysql -> raw -> dbt marts, tested",
    start_date=datetime(2026, 9, 1),
    schedule="0 3 * * *",
    catchup=False,
    max_active_runs=1,
    default_args=default_args,
    tags=["ecom"],
):
    # run() returns the per-table row counts, which land in xcom
    extract = PythonOperator(task_id="extract_to_raw", python_callable=run)

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=f"{DBT} run --project-dir {DBT_DIR} --profiles-dir {DBT_DIR}",
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"{DBT} test --project-dir {DBT_DIR} --profiles-dir {DBT_DIR}",
    )

    extract >> dbt_run >> dbt_test
