# 0002. Deterministic signal processing, no machine learning

- Status: accepted
- Date: 2026-11-02

## Context and problem

Bird monitoring from audio is often done with species classifiers. A
classifier's output depends on training data, can fail silently on
unfamiliar microphones, codecs and soundscapes, needs accelerators or large
runtimes on small devices, and is hard to explain to someone who wants to
know why a number changed.

The question this platform answers is about **soundscape activity** (how
active, when, under what conditions, and how trustworthy the measurement is),
not species identity. Published acoustic indices, event detectors and
robust statistics answer that question directly.

## Options considered

1. Run a pre-trained species classifier at the edge.
2. Ingest detections produced by third-party classifiers.
3. Use only deterministic, documented signal processing and statistics.

## Decision

Option 3. Every number the platform produces is a documented function of the
audio or of other data, with parameters that are written down and citable:

- acoustic indices (ACI, ADI, AEI, BI, NDSI, entropy, BGN, SNR, EVN, ACT),
  per minute and per frequency bin;
- band-limited energy event detection with hysteresis thresholds;
- threshold rules for quality control (rain, wind, clipping, dropouts);
- robust statistics (rolling median and MAD) for baselines.

The platform contains no trained models, no inference, no embeddings, no
machine-learning libraries, and no datasets meant for training or evaluating
models. Sources whose content is produced by classifiers are not ingested.

## Consequences

- Good: results are reproducible bit-for-bit from the same input and
  configuration, and explainable down to the formula.
- Good: the DSP runs well above real time on a Raspberry Pi-class CPU.
- Good: no model licences, model downloads or accelerators.
- Bad: no species-level output. The platform says "the bird band was 40 %
  more active than usual at dawn", not "a blackbird sang".
- Bad: indices are imperfect proxies; the docs say so (see
  [research notes](../research.md#21-acoustic-indices)) and every index is
  shown with its QA flags.
- Follow-up work: index reference pages with formulas and caveats (M2.17);
  golden tests against an independent implementation (M2.14).
