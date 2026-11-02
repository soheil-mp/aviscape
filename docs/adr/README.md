# Architecture decision records

Significant decisions are recorded here in the
[MADR](https://adr.github.io/madr/) format: context, options, decision and
consequences. A decision is changed by writing a new record that supersedes
the old one, never by editing history away.

| No. | Decision | Status |
| :-- | :-- | :-- |
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions | accepted |
| [0002](0002-deterministic-signal-processing-without-machine-learning.md) | Deterministic signal processing, no machine learning | accepted |
| [0003](0003-raw-audio-never-leaves-memory.md) | Raw audio never leaves memory | accepted |
| [0004](0004-kafka-avro-and-karapace-for-streaming.md) | Kafka, Avro and Karapace for streaming | accepted |
| [0005](0005-ducklake-on-s3-compatible-storage.md) | DuckLake on S3-compatible storage | accepted |
| [0006](0006-dagster-and-dbt-for-batch.md) | Dagster and dbt for the batch platform | accepted |
| [0007](0007-storage-and-bandwidth-budgets-as-code.md) | Storage and bandwidth budgets as code | accepted |

Start a new record from [template.md](template.md).
