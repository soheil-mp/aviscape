# 0008. BirdWeather detections as labelled third-party context

- Status: accepted (amends the source rule in [0002](0002-deterministic-signal-processing-without-machine-learning.md))
- Date: 2026-11-02

## Context and problem

The acoustic indices say how active a soundscape is, not which birds are
singing. [BirdWeather](https://www.birdweather.com/) runs a public network of
community listening stations whose detections are produced by the BirdNET
classifier on the station or in BirdWeather's cloud, and exposes them through
a public GraphQL API (`https://app.birdweather.com/graphql`, no key, checked
on 2 November 2026). It offers aggregate queries (`counts`, `topSpecies`,
`dailyDetectionCounts`, all filterable by a bounding box) and a real-time
subscription (`newDetection`, filterable by station, country and score).

Showing "which species nearby stations are reporting right now" next to our
own measurements makes the dashboard far more useful. But:

- [ADR 0002](0002-deterministic-signal-processing-without-machine-learning.md)
  keeps this platform free of machine learning, and these detections are the
  output of someone else's classifier.
- BirdWeather's [terms of service](https://www.birdweather.com/terms-of-service)
  (last updated 22 October 2022) grant personal, non-commercial use and
  prohibit crawling or scraping data by automated means and copying or
  storing any significant portion of the content. They do not mention the
  public API.
- Stations are often in private gardens; station records carry a name, a
  location and a `locationPrivacy` flag.

## Options considered

1. Do not use BirdWeather.
2. Ingest individual detections (and their soundscape audio) into the lake.
3. Use BirdWeather only as labelled, aggregated, third-party context, under
   strict limits, after confirming the use with BirdWeather.

## Decision

Option 3.

- **No machine learning in this project still holds.** aviscape never runs,
  trains, fine-tunes, evaluates or benchmarks a model. BirdWeather's output
  is treated like weather data: an external observation shown as context.
- **No evaluation of the detections.** The platform computes no accuracy,
  agreement, precision or recall between BirdWeather detections and anything
  else, and never uses them as labels or ground truth.
- **Aggregates only.** Stored data is detection counts per species, per
  0.1° grid cell, per hour (batch) or per 15 minutes (live), plus the number
  of contributing stations. No detection-level rows, no confidence scores per
  detection, no soundscape audio or audio URLs.
- **No personal data.** Station names and IDs are not stored; station IDs
  exist only in memory to filter the live subscription. Stations with
  `locationPrivacy` enabled are excluded.
- **Light, polite use.** At most a few aggregate queries per grid cell per
  hour, one subscription connection, caching, backoff, and a `User-Agent`
  that links to this repository.
- **Confirm first.** The connector ships disabled by default and is switched
  on only after BirdWeather confirms in writing that this non-commercial,
  aggregate-only use of the public API is acceptable (roadmap item M8.11).
- **Labelled everywhere.** The API and the dashboard present the counts as
  "automated detections by BirdNET on BirdWeather community stations,
  unverified", with attribution and a link.

## Consequences

- Good: users see likely species context next to the soundscape activity
  measured here, in real time.
- Good: the core pipeline stays deterministic and explainable; the external
  context can be switched off without affecting any computed value.
- Bad: depends on a third party's goodwill and terms; the connector has a
  kill switch in configuration and degrades gracefully when disabled.
- Bad: automated detections contain false positives; the platform shows them
  as reported, labelled, and never derives its own claims from them.
- Follow-up work: M6.11, M8.11, M8.12, M9.9, M12.9.
