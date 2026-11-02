# 0004. Kafka, Avro and Karapace for streaming

- Status: accepted
- Date: 2026-11-02

## Context and problem

Features arrive continuously from several edge agents, must be validated,
deduplicated and enriched in event time, and must reach the lake exactly
once. Several consumers read the same data (lake sink, live API, alerting).
The backbone has to run on a laptop in Docker and on Kubernetes, under a
permissive licence.

## Options considered

1. Apache Kafka 4.x in KRaft mode (Apache-2.0).
2. Redpanda (Kafka API; community edition under the Business Source Licence).
3. NATS JetStream (Apache-2.0).
4. MQTT broker at the edge, bridged into a database.

For schemas: JSON without a registry; JSON Schema; Avro or Protobuf with a
registry (Confluent Schema Registry under the Confluent Community Licence,
Apicurio, or Karapace under Apache-2.0).

For processing: Apache Flink / PyFlink, Quix Streams, Bytewax, Faust
(community fork), plain consumers.

## Decision

- **Apache Kafka 4.x, KRaft mode.** ZooKeeper-free since 4.0, so a single
  container is enough locally; Strimzi runs it on Kubernetes. Transactions
  give exactly-once between topics; compacted topics hold the sensor
  registry and status.
- **Avro with Karapace.** Compact binary records with schema evolution rules
  enforced by the registry (`BACKWARD_TRANSITIVE`), Confluent-compatible API,
  Apache-2.0.
- **Quix Streams** for stateful stream processing in Python: windowing,
  state stores and exactly-once processing without operating a JVM cluster.
  The DSP stays in the edge agent; stream processing only validates,
  deduplicates, enriches and aggregates.

## Consequences

- Good: an industry-standard backbone with clear delivery semantics.
- Good: schema changes that would break consumers fail in CI (M4.5) and at
  registration time.
- Bad: Kafka is heavier than NATS or MQTT for a handful of sensors; the
  single-node KRaft setup and byte-capped topics keep that cost small.
- Bad: Quix Streams is younger than Flink; the processing logic is kept in
  plain functions so it can move if needed.
- Follow-up work: M4, M5.5, M6.
