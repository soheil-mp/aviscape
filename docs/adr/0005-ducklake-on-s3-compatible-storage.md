# 0005. DuckLake on S3-compatible storage

- Status: accepted
- Date: 2026-11-02

## Context and problem

The lake receives many small writes (a few rows per sensor per minute), must
support exactly-once ingestion, time travel for reproducible reports,
schema evolution, and cheap analytical queries from dbt and the API. It must
run on a laptop with little disk and stay object-store-native so that it can
move to any S3-compatible service.

## Options considered

Table formats:

1. Apache Iceberg (PyIceberg, a REST catalog).
2. Delta Lake (delta-rs).
3. DuckLake 1.0: Parquet data files and a SQL database as the catalog.
4. Plain Parquet files plus DuckDB.

Object storage: MinIO community edition, SeaweedFS, Garage, RustFS, local
filesystem.

## Decision

- **DuckLake 1.0 with a PostgreSQL catalog.** Released on 13 April 2026 with
  a stable specification and MIT licence. Metadata operations are SQL
  transactions, which lets the lake sink store Kafka offsets in the same
  transaction as the data it writes, giving exactly-once ingestion without
  extra machinery. Data inlining (on by default in 1.0) keeps tiny streaming
  inserts in the catalog until they are flushed into Parquet in bulk, which
  avoids the small-files problem.
- **SeaweedFS** for the S3 API (Apache-2.0, actively maintained). MinIO's
  community edition stopped shipping binaries and images in October 2025 and
  went into maintenance mode in December 2025. Garage is AGPL-3.0 and RustFS
  is still young. All storage access goes through the S3 API, so the store
  can be swapped.

## Consequences

- Good: one engine (DuckDB) for the sink, dbt and the API.
- Good: snapshots give time travel for reproducible reports (M7.6).
- Bad: DuckLake is newer than Iceberg and has a smaller ecosystem. The data
  stays plain Parquet, so a move to Iceberg remains possible (DuckLake 1.0
  added Iceberg-compatible bucket partitioning and deletion buffers).
- Bad: maintenance (flushing inlined data, merging files, expiring
  snapshots) must be scheduled; Dagster owns it (M7.4, M8.6).
- Follow-up work: M7.
