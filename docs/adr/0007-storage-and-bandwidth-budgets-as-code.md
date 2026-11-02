# 0007. Storage and bandwidth budgets as code

- Status: accepted
- Date: 2026-11-02

## Context and problem

The platform must run on a laptop with little free disk. Streams are
unbounded: without limits, topic logs, lake files and caches grow until the
disk is full. Live streams also cost bandwidth: about 1.4 GB per day for one
128 kbit/s stream listened to continuously.

## Options considered

1. Rely on retention settings scattered across Kafka, the lake and caches.
2. Monitor disk usage and clean up by hand.
3. Declare budgets in one configuration file, derive every limit from it,
   measure usage continuously and enforce the budget automatically.

## Decision

Option 3.

- **One file** (`config/budgets.yaml`) declares the total storage budget
  (default 2 GiB), the share of each dataset, retention per tier, the
  maximum number of live streams (default 5) and the default duty cycle.
- **Derived limits**: Kafka `retention.bytes` per topic, lake retention per
  table, the edge spool size and cache sizes are generated from it.
- **Measurement**: a Dagster asset records bytes per table, bucket, catalog
  and topic every hour (M7.7), exposed as metrics.
- **Enforcement**: an asset check fails above 100 % and warns above 80 %; a
  maintenance job trims data in a documented priority order (oldest hot
  spectral data first, summary indices last).
- **Bandwidth**: the default dawn-weighted duty cycle listens continuously
  from nautical dawn to three hours after sunrise and one minute in five
  otherwise, about a third of the day.

## Consequences

- Good: the platform cannot fill the disk by accident.
- Good: the cost of each dataset is visible and discussed in reviews.
- Bad: some history is deliberately lost; the docs state what is kept for how
  long ([research notes, section 8](../research.md#8-sizing-storage-and-bandwidth)).
- Follow-up work: M6.1, M7.5, M7.7, M8.6.
