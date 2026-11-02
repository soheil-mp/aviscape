# 0003. Raw audio never leaves memory

- Status: accepted
- Date: 2026-11-02

## Context and problem

Open microphones and garden recorders pick up more than birds: people
talking, passing, working. Storing that audio would mean storing personal
data about people who never agreed to it. It would also break the storage
budget: one continuous stream is about 8 GB per day as 16-bit PCM at
48 kHz.

## Options considered

1. Store raw audio and delete it after a retention period.
2. Store short clips around detected events.
3. Store clips but filter speech first.
4. Keep audio in memory only and emit derived features.

## Decision

Option 4. The edge agent decodes each stream into a bounded in-memory buffer,
computes features for each 60-second window and discards the samples. What
leaves the agent:

- minute-level summary indices and QA metrics;
- minute-level per-frequency-bin spectral indices;
- event descriptors (start, duration, frequency bounds, peak level);
- one-second third-octave band levels for the live view, kept for 24 hours
  in Kafka and never written to the lake.

None of these can be turned back into intelligible speech: they are
aggregated over a minute, or over a second in about 30 bands, far below the
time and frequency resolution speech needs.

Speech filtering (option 3) was rejected because no filter is perfect and the
safest audio to store is none. Personal fields in source metadata (such as a
stream owner's name) are dropped at the connector, and microphone
coordinates are coarsened to a 0.1° grid cell.

## Consequences

- Good: no personal data at rest from live sources, and 0 bytes of audio at
  rest.
- Good: the edge sends a few hundred bytes per minute instead of megabytes.
- Bad: no "listen back" feature for live sources. The synthetic generator and
  the optional, licence-filtered xeno-canto corpus cover demos and debugging.
- Bad: index bugs cannot be fixed retroactively for live data. Mitigation:
  golden tests and replayable synthetic scenarios (M2.14, M3.7).
- Follow-up work: tests that audit filesystem writes from the edge agent and
  scan logs and traces for audio payloads (M5.8).
