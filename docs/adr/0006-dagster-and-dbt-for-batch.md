# 0006. Dagster and dbt for the batch platform

- Status: accepted
- Date: 2026-11-02

## Context and problem

Next to the stream, the platform needs scheduled and event-driven batch
work: pulling weather and context data, syncing the stream catalogue,
building the dimensional model, running quality checks, compacting the lake
and enforcing budgets. This work should be declared as data assets with
lineage, partitions, freshness expectations and checks, not as opaque cron
jobs.

## Options considered

Orchestration: Apache Airflow 3, Prefect 3, Kestra, Dagster.

Transformations: dbt-core with dbt-duckdb, SQLMesh, Python-only
transformations.

## Decision

- **Dagster** (1.13 line). Software-defined assets match the lake's tables
  one to one; partitions model hourly weather and daily marts; asset checks
  and freshness policies express data quality and timeliness; sensors react
  to new sensors in the stream catalogue. Components and the `dg` CLI are
  generally available since 1.12.
- **dbt-core 1.x with dbt-duckdb**, attached to DuckLake. Model contracts,
  tests, unit tests, documentation and exposures are mature and widely
  known. dbt models appear in Dagster as assets, so lineage is one graph.
  dbt Core v2 (the Rust engine) is in alpha after the dbt Labs and Fivetran
  merger; the project stays on 1.x until v2 is stable and supports
  dbt-duckdb.
- Python 3.13 is the baseline, because dbt-core 1.11 supports Python up to
  3.13. Packages that do not depend on dbt are also tested on 3.14.

## Consequences

- Good: one asset graph from external APIs to marts, with checks attached.
- Good: SQL models are reviewable by anyone who reads SQL.
- Bad: two tools to learn instead of one.
- Bad: tool churn around dbt; the models are plain SQL and portable.
- Follow-up work: M8, M9.
