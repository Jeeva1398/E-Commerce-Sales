-- read-only login for the streamlit dashboard. run once in the supabase sql editor
-- after the first pipeline run (the marts schema has to exist first).
-- change the password before running it.

create role dashboard_ro with login password 'change-me';

grant usage on schema analytics_marts to dashboard_ro;
grant select on all tables in schema analytics_marts to dashboard_ro;

-- dbt drops and recreates the mart tables every run, so grants on the existing
-- tables alone would be lost the next morning
alter default privileges for role postgres in schema analytics_marts
    grant select on tables to dashboard_ro;
