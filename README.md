# aviscape

Real-time, model-free monitoring of bird soundscapes. aviscape listens to
live open microphones, turns every minute of sound into published acoustic
indices at the edge, and streams them through Kafka into a DuckLake
lakehouse, where they are joined with weather and sun position,
quality-checked and served to a live dashboard.

> **Status: planning.** The research, architecture and a 728-hour roadmap
> are done; implementation starts with milestone M0. There is no runnable
> code yet. See [Status and plans](#status-and-plans).

## What it will do

- **Listen live** to open microphones from the
  [Locus Sonus](https://locusonus.org/soundmap/) network, your own
  microphone, or a built-in synthetic soundscape simulator.
- **Measure, not guess.** Compute published soundscape measures every minute
  (Acoustic Complexity, Acoustic Diversity and Evenness, Bioacoustic Index,
  NDSI, acoustic entropy, background noise, event rate), plus discrete
  acoustic events. No species classifier and no trained model: every number
  is a documented formula with a citation.
- **Keep audio private.** Audio exists only in memory for one minute. Only
  derived numbers leave the listening process, and personal fields in source
  metadata are dropped at the door.
- **Put it in context:** weather, sun position, GBIF species records and the
  species that nearby [BirdWeather](https://www.birdweather.com/) community
  stations report in real time. Those reports come from BirdWeather's own
  automated detector; aviscape shows them only as aggregated, clearly
  labelled third-party context and never computes anything from them.
- **Show the soundscape as it happens:** a false-colour spectrogram of the
  whole day that grows minute by minute, dawn chorus onset on a sun-relative
  clock, and activity trends with rain and wind marked as unreliable.
- **Run like a production data platform:** data contracts from the edge to
  the marts, event-time streaming with exactly-once ingestion, orchestrated
  batch enrichment, quality checks, storage and bandwidth budgets as code,
  full observability, and GitOps on Kubernetes.

### What is new about it

| Idea | Why it matters |
| :-- | :-- |
| Deterministic edge DSP instead of classifiers | explainable, reproducible bit-for-bit, runs on a Raspberry Pi |
| Live long-duration false-colour spectrograms | a 24-hour view of the soundscape that updates every minute, not after the fact |
| Sun-relative time axis | compares mornings across seasons and sites by minutes from civil dawn |
| Weather-aware quality control | rain and wind flags from the audio itself, cross-checked with weather data |
| Exactly-once streaming into DuckLake | Kafka offsets committed in the same catalog transaction as the data |
| Privacy by construction | 0 bytes of audio at rest from live sources |
| Budgets as code | a 2 GiB storage budget and a bandwidth duty cycle, measured and enforced |

## Who it's for

- **Naturalists and birders** who want to see how active the dawn chorus is
  at a place, right now and over the season.
- **Students and researchers in soundscape ecology** who need an open,
  explainable and reproducible pipeline for acoustic indices.
- **Data and platform engineers** looking for a complete, realistic
  reference of a streaming and lakehouse platform, built on open data that
  is not about people.

## Built with

| Layer | Tools |
| :-- | :-- |
| Signal processing | Python 3.13, NumPy, SciPy, PyAV |
| Streaming | Apache Kafka 4 (KRaft), Avro, Karapace, Quix Streams |
| Lakehouse | DuckLake 1.0, DuckDB, SeaweedFS (S3 API), PostgreSQL |
| Batch | Dagster, dbt-core with dbt-duckdb |
| Contracts and quality | Open Data Contract Standard v3.1, datacontract-cli, dbt tests, Dagster asset checks |
| Serving | FastAPI, server-sent events; TypeScript, Vite and MapLibre GL dashboard |
| Platform | Docker Compose, kind, Helm 4, Strimzi, CloudNativePG, Argo CD, KEDA, Envoy Gateway |
| Observability | OpenTelemetry, Grafana, Prometheus, Loki, Tempo |
| Engineering | uv, Ruff, mypy, pytest, Hypothesis, pre-commit, gitleaks, GitHub Actions, release-please, Renovate, cosign, syft, Zensical |

The reasons behind each choice are in the
[architecture decision records](docs/adr/).

## How to run it

**Today** there is nothing to run, only documents to read:

```sh
git clone https://github.com/soheil-mp/aviscape.git
cd aviscape
pre-commit install   # secret scanning and hygiene checks on every commit
```

| Read | For |
| :-- | :-- |
| [ROADMAP.md](ROADMAP.md) | the plan: 20 milestones, 163 work items with estimates and acceptance criteria |
| [docs/research.md](docs/research.md) | the science, prior work, tool landscape and sizing |
| [docs/architecture.md](docs/architecture.md) | the target system: components, topics, lake layout, guarantees |
| [docs/data-sources.md](docs/data-sources.md) | every data source, its terms and how personal data is kept out |
| [docs/adr/](docs/adr/) | the architecture decisions |

**From v0.1.0** (milestone M1) the walking skeleton will run with Docker,
[uv](https://docs.astral.sh/uv/) and [just](https://just.systems/):

```sh
cp .env.example .env
just up      # Kafka, the edge agent on synthetic audio, the API
just demo    # replays one synthetic hour in under a minute
curl localhost:8000/v1/sensors/synthetic-1/minutes
```

## Status and plans

| Done | Next |
| :-- | :-- |
| Research, target architecture, data-source register, eight ADRs, roadmap; repository with MIT licence and secret scanning | M0: toolchain, CI and docs site. M1: the walking skeleton (v0.1.0) |

The work ahead is in [ROADMAP.md](ROADMAP.md) and the issues. Releases
follow the milestones: real-time monitoring of live microphones arrives with
v0.3.0, the dashboard and a public demo built from synthetic data with
v0.5.0, Kubernetes and GitOps with v0.7.0, and the field-tested 1.0 after
that.

## Data sources and attribution

Live sounds: Locus Sonus – Locustream open microphones
([www.locusonus.org](https://locusonus.org/)). Weather data by
[Open-Meteo.com](https://open-meteo.com/) (CC BY 4.0). Species context:
[GBIF.org](https://www.gbif.org/). Nearby detections:
[BirdWeather](https://www.birdweather.com/) (automated detections from
community stations, unverified; the connector stays off until BirdWeather
confirms the use). Map data © OpenStreetMap contributors.
Terms and data minimisation for each source are in
[docs/data-sources.md](docs/data-sources.md). The repository and the public
demo contain synthetic data only.

## License

MIT, see [LICENSE](LICENSE).
