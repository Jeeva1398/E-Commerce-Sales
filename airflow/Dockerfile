FROM apache/airflow:2.10.5

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*
USER airflow

# dbt lives in its own venv - it and airflow pin conflicting jinja2/protobuf
# versions and installing them side by side breaks one or the other
RUN python -m venv /home/airflow/dbt-venv \
    && /home/airflow/dbt-venv/bin/pip install --no-cache-dir dbt-core==1.11.15 dbt-postgres==1.11.0
