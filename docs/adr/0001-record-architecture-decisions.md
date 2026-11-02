# 0001. Record architecture decisions

- Status: accepted
- Date: 2026-11-02

## Context and problem

The platform combines signal processing, streaming, a lakehouse, batch
orchestration and Kubernetes. Many choices are made early, and several tools
in this space changed licence or maintenance status in 2025–2026. Without a
record, later contributors (and later versions of us) cannot tell whether a
choice was deliberate or accidental, or what it would take to revisit it.

## Options considered

1. No formal record; rely on commit messages and the README.
2. A design document that is edited over time.
3. Architecture decision records: one short, immutable file per decision.

## Decision

Option 3, in the MADR format, stored in `docs/adr/` and published with the
docs site. Records are numbered, never deleted, and superseded by new
records when a decision changes. Every pull request that makes a significant
decision (new runtime dependency, new data source, change of guarantee or
budget) adds or updates a record.

## Consequences

- Good: decisions are reviewable in pull requests and visible in the docs.
- Good: the research behind a decision is linked rather than retold.
- Bad: a small amount of writing per decision.
- Follow-up work: M0.11 renders the records in the docs site.
