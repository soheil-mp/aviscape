# Research notes

These notes are the evidence behind the [roadmap](../ROADMAP.md) and the
[architecture decisions](adr/). They cover the science (what can be measured
about birds from sound without a classifier), prior work, the data sources and
their terms, and the state of the tools as of **2 November 2026**.

Where a claim depends on a fast-moving project (a release, a licence, a
maintenance status), the date it was checked is stated. Re-check these before
relying on them; [M0](../ROADMAP.md#m0--foundations-and-engineering-standards)
and the quarterly licence review in [M10.7](../ROADMAP.md#m10--data-quality-and-governance)
keep them current.

## Contents

1. [Problem framing](#1-problem-framing)
2. [Measuring bird activity without a classifier](#2-measuring-bird-activity-without-a-classifier)
3. [Data quality problems specific to field audio](#3-data-quality-problems-specific-to-field-audio)
4. [What "real time" means for this project](#4-what-real-time-means-for-this-project)
5. [Prior work and what is new here](#5-prior-work-and-what-is-new-here)
6. [Data sources](#6-data-sources)
7. [Tool landscape (checked 2 November 2026)](#7-tool-landscape-checked-2-november-2026)
8. [Sizing: storage and bandwidth](#8-sizing-storage-and-bandwidth)
9. [References](#9-references)

---

## 1. Problem framing

**Passive acoustic monitoring** (PAM) records the environment with unattended
microphones and analyses the sound afterwards. It scales better than human
point counts, works at night and leaves a permanent record (Sugai et al.,
2019; Gibb et al., 2019).

**Soundscape ecology** studies the whole acoustic environment rather than
individual species. A soundscape is split into three sources (Pijanowski et
al., 2011):

| Component | Source | Typical examples |
| :-- | :-- | :-- |
| Biophony | animals | bird song and calls, insects, amphibians |
| Geophony | non-biological nature | rain, wind, running water, thunder |
| Anthrophony | people | traffic, aircraft, machinery, voices |

Birds dominate the biophony of most temperate soundscapes in the morning, and
most bird song falls roughly between 2 and 8 kHz. Both facts matter for the
design: the **dawn chorus** gives a strong, daily, time-locked signal, and the
2–8 kHz band separates most bird sound from low-frequency traffic and wind.

The project's question is therefore not "which species is singing?" but:

> How active is the bird soundscape at each microphone, minute by minute, how
> does that activity move with dawn, season and weather, and how much of the
> signal can we trust?

That question can be answered with published, deterministic signal-processing
methods. It needs no trained model, which keeps every number explainable,
reproducible bit-for-bit and cheap enough to compute on a Raspberry Pi
([ADR 0002](adr/0002-deterministic-signal-processing-without-machine-learning.md)).

## 2. Measuring bird activity without a classifier

### 2.1 Acoustic indices

Acoustic indices summarise the distribution of sound energy in time and
frequency over a window, usually one minute. The platform implements the
following, each with its original parameters as defaults:

| Index | Measures | Reference | Notes for implementation |
| :-- | :-- | :-- | :-- |
| ACI (Acoustic Complexity Index) | frame-to-frame intensity variability per frequency bin; high for modulated sounds like song, low for constant noise | Pieretti, Farina & Morri (2011) | temporal step and frequency band are parameters; also used per bin in false-colour spectrograms |
| ADI (Acoustic Diversity Index) | Shannon diversity of energy across frequency bands above a dB threshold | Villanueva-Rivera et al. (2011) | default 1 kHz bands up to 10 kHz, −50 dBFS threshold |
| AEI (Acoustic Evenness Index) | Gini coefficient of the same band occupancy | Villanueva-Rivera et al. (2011) | inverse behaviour to ADI |
| BI (Bioacoustic Index) | area under the mean spectrum above its minimum within 2–8 kHz | Boelman et al. (2007) | the bird band default |
| NDSI (Normalised Difference Soundscape Index) | (biophony − anthrophony) / (biophony + anthrophony) | Kasten et al. (2012) | defaults: anthrophony 1–2 kHz, biophony 2–11 kHz |
| H, Ht, Hf (acoustic entropy) | evenness of the amplitude envelope (Ht) and the spectrum (Hf); H = Ht × Hf | Sueur et al. (2008) | Ht near 1 for noise, lower for impulsive sound |
| BGN, SNR, EVN, ACT | background noise, signal-to-noise, event rate, acoustic activity | Towsey (2017) | BGN from the mode of the dB distribution per bin |

**Known limits.** A meta-analysis of 34 studies and 364 effect sizes found
that indices track biodiversity only moderately and inconsistently; entropy,
NDSI and ACI performed best, and the authors warn against using a single
index as a surrogate for diversity (Alcocer et al., 2022). The project
follows that advice:

- indices are presented as **soundscape activity measures**, never as species
  counts or "biodiversity scores";
- every index is reported with the QA flags of its minute (rain, wind,
  clipping, dropouts), because geophony inflates several indices;
- comparisons are made **within a sensor over time** first, and across sensors
  only on a sun-relative time axis.

### 2.2 Long-duration false-colour spectrograms

Towsey and colleagues showed that three spectral indices computed per
frequency bin per minute (for example ACI, temporal entropy and event rate)
can be mapped to the red, green and blue channels of an image. A 24-hour
recording becomes one 1440-pixel-wide picture in which dawn chorus, insects,
rain and traffic are visible at a glance (Towsey et al., 2014; Towsey et al.,
2018). Typical settings are 22.05 kHz audio and 512-sample frames, giving 256
frequency bins of about 43 Hz.

The project computes these spectral indices at the edge and renders the image
**while the day is still running**: a live, growing false-colour spectrogram
per microphone. We found no open platform that streams this view live; most
use it as an offline, after-the-fact visualisation.

### 2.3 Deterministic event detection

A band-limited energy detector with hysteresis (start above BGN + *a* dB,
end below BGN + *b* dB, minimum duration and gap) finds discrete acoustic
events and reports their time, duration, frequency bounds and peak level.
Event counts per minute in the bird band are a simple, robust activity measure
that complements the indices. No labels and no training are involved.

### 2.4 Dawn chorus timing

Dawn chorus onset varies with season, weather and ambient light (Bruni,
Mennill & Foote, 2014). To compare days and sites, the platform puts time on
a **sun-relative axis**, expressed as minutes from civil dawn, computed
locally from coordinates. Onset is detected deterministically: the first
sustained run of minutes where bird-band activity exceeds the sensor's own
baseline for that sun-relative minute.

### 2.5 Statistical baselines

"Unusual" activity is defined with robust statistics, not a model: a rolling
14-day median and median absolute deviation (MAD) per sensor and sun-relative
minute, and a robust z-score against them. These are transparent, need no
training data, and stay meaningful with the small data volumes the project
keeps.

## 3. Data quality problems specific to field audio

| Problem | Effect | Detection used here |
| :-- | :-- | :-- |
| Rain | broadband impulsive energy; inflates ACI and event counts | two-band power and SNR thresholds after hardRain (Metcalf et al., 2020), cross-checked against hourly precipitation from Open-Meteo |
| Wind | low-frequency rumble and microphone buffeting | low-band energy ratio, cross-checked against hourly wind speed |
| Clipping | flattened peaks, spurious high-frequency energy | share of samples at full scale |
| Dropouts and digital silence | gaps that look like "quiet" | runs of exact zeros, decoder underruns, missing windows |
| DC offset, hum | biased low-frequency bins | mean offset, narrow-band persistence at mains frequencies |
| Stuck sensor | identical values for hours | flatline detection on indices |
| Clock and timestamp error | minutes assigned to the wrong time | drift between sample counter and wall clock; explicit time-uncertainty field |
| Human speech | privacy risk | never stored: raw audio stays in memory; only minute-level features leave the edge ([ADR 0003](adr/0003-raw-audio-never-leaves-memory.md)) |

hardRain reached up to 99 % accuracy on tropical data but did worse at
temperate sites with dense broadleaf vegetation (Metcalf et al., 2020), which
is why the weather cross-check is part of the design rather than an extra.

## 4. What "real time" means for this project

Live internet audio streams (Icecast/HTTP MP3 or Ogg) carry **no capture
timestamps**, and players and servers buffer a few seconds to tens of
seconds. Minute-level features make this harmless if it is handled
explicitly:

- **Event time** is the arrival time of the first sample of a window minus a
  per-stream latency estimate, aligned to UTC minute boundaries, and carries a
  `time_uncertainty_s` field.
- **Latency targets** (see [SLOs in the roadmap](../ROADMAP.md#5-service-level-objectives)):
  a closed one-minute window should reach the live API within 15 seconds at
  p95, the lake within 5 minutes, and the marts within an hour.
- **Live but ephemeral**: one-second third-octave band levels feed the live
  view through a short-retention topic and are never written to the lake.

## 5. Prior work and what is new here

| Prior work | What it shows | How this project differs |
| :-- | :-- | :-- |
| Sethi et al. (2018): Raspberry Pi monitoring device over mobile networks | low-cost networked recorders can run continuously in the field for weeks | ships features, not audio, and adds the data platform around the device |
| Towsey et al. (2014, 2018): false-colour spectrograms | three spectral indices make 24 h of sound legible in one image | computed incrementally and streamed live |
| Metcalf et al. (2020): hardRain | rain can be flagged with simple two-band thresholds | combined with weather data as a cross-check, applied in-stream |
| Orcasound: live hydrophone streaming to S3 as HLS | open, live, public audio pipelines for citizen science | birds instead of whales; features instead of audio at rest |
| Cyberforest (Saito et al., 2015): live forest sound streams since 1995 used for remote bird censuses | live streams are good enough for bird monitoring by ear | automated, quantitative and reproducible measures over the same kind of stream |
| Locus Sonus Locustream: a worldwide network of open microphones | a public, legally reusable set of live sources | first-class connector with privacy minimisation |

What is new is the combination: deterministic edge DSP, privacy by
construction, event-time streaming with exactly-once ingestion into a
lakehouse, data contracts from the edge to the marts, weather-aware quality
control, and storage and bandwidth budgets enforced as code.

## 6. Data sources

The full register, with attribution text, terms and minimisation rules per
source, is in [data-sources.md](data-sources.md). Summary of what was
verified on 2 November 2026:

- **Locus Sonus Locustream** publishes its active open microphones as JSON
  (`https://locusonus.org/soundmap/list/active/json/name`, 51 streams on the
  day checked) with Icecast MP3/Ogg URLs. Its terms of use allow anyone to
  listen to, record, adapt and distribute the sound, ask users to cite Locus
  Sonus, and leave responsibility for third-party complaints with the user.
  Each entry carries a person's name (`artist`) and coordinates; the
  connector drops the name and coarsens the coordinates.
- **xeno-canto API v3** needs a personal API key that must not be published
  in git; licences are per recording (Creative Commons variants). Only used
  for an optional, size-capped replay corpus; recordings with NoDerivatives
  licences are excluded and no audio is redistributed.
- **Open-Meteo** gives hourly weather and an ERA5-based archive, free for
  non-commercial use under CC BY 4.0 with attribution, below about 10,000
  calls per day.
- **GBIF** occurrence search supports facet counts, so monthly bird species
  counts per area can be read without touching record-level data.
- **BirdWeather** exposes detections from its community stations through a
  public GraphQL API without a key: aggregate queries (`counts`,
  `topSpecies`, `dailyDetectionCounts`) filterable by a bounding box, and a
  real-time `newDetection` subscription filterable by station, country and
  score. Detections are produced by the BirdNET classifier. Its terms of
  service (last updated 22 October 2022) allow personal, non-commercial use,
  forbid automated crawling or scraping and storing a significant portion of
  the content, and do not mention the API. aviscape therefore uses it only
  as labelled, aggregate-only context, disabled until BirdWeather confirms
  the use ([ADR 0008](adr/0008-birdweather-detections-as-third-party-context.md)).
  Station records carry names and a location-privacy flag; names are not
  stored and private stations are excluded.

Considered and **not used**: eBird (needs a key, and its terms restrict
sharing; may return as an optional connector, see the roadmap's open
questions).

## 7. Tool landscape (checked 2 November 2026)

| Area | Finding | Consequence for this project |
| :-- | :-- | :-- |
| Object storage | MinIO's community edition stopped shipping binaries and images in October 2025 and entered maintenance mode on 3 December 2025 | use SeaweedFS (Apache-2.0) behind the S3 API; keep storage code S3-generic |
| Table format | DuckLake 1.0 was released on 13 April 2026: Parquet data, SQL catalog (PostgreSQL, SQLite or DuckDB), data inlining on by default, MIT licence | use DuckLake with a PostgreSQL catalog; inlining suits small streaming writes |
| Streaming | Apache Kafka 4.0 removed ZooKeeper; 4.2 (February 2026) made share groups (queues) production-ready; 4.3 followed in May 2026 | Kafka 4.x in KRaft mode |
| Stream processing | Quix Streams 3.x: Apache-2.0, pure Python, stateful windows, exactly-once via Kafka transactions | Quix Streams for in-stream validation, dedup and enrichment |
| Orchestration | Dagster 1.12 (October 2025) made Components and the `dg` CLI generally available; 1.13.x is current | Dagster with software-defined assets and asset checks |
| Transformations | dbt Labs and Fivetran merged (announced October 2025); dbt Core v2.0 (Rust engine) is in alpha; dbt-core 1.11 supports Python up to 3.13 | dbt-core 1.x with dbt-duckdb; Python 3.13 baseline; revisit v2 when stable |
| Data contracts | Open Data Contract Standard v3.1.0 is current; `datacontract-cli` lints, tests and diffs contracts | ODCS contracts checked in CI |
| Data quality | Soda Core v4 refocused on data contracts | dbt tests + Dagster asset checks + domain QA; Soda not needed |
| Python tooling | `ty` (Astral) is still beta (0.0.x, October 2026) | Ruff + mypy `--strict`; evaluate ty at 1.0 |
| Docs | Material for MkDocs entered maintenance mode in November 2025; its authors build Zensical, which reads `mkdocs.yml` | Zensical for the docs site |
| Kubernetes ingress | ingress-nginx was retired (best-effort maintenance ended March 2026); Gateway API is the recommended path | Gateway API with Envoy Gateway on kind |
| Packaging Kubernetes apps | Helm 4.0 was released in November 2025 | Helm 4 charts |

## 8. Sizing: storage and bandwidth

The platform must run on a laptop with little free disk, so data volume is a
design input ([ADR 0007](adr/0007-storage-and-bandwidth-budgets-as-code.md)).
Upper bounds for the default configuration (5 live microphones, continuous
listening, uncompressed sizes; Parquet with zstd usually cuts these several
times, to be measured in M7.7):

| Dataset | Resolution | Retention | Bytes per sensor-day | 5 sensors, full retention |
| :-- | :-- | :-- | --: | --: |
| Summary indices + QA | 1 row per minute, ~40 numeric fields (~160 B) | 365 days | 230 KB | 0.42 GB |
| Spectral indices, hot | 256 bins × 5 indices, float32 | 7 days | 7.4 MB | 0.26 GB |
| Spectral indices, cold | 128 bins × 3 indices, uint8 | 90 days | 553 KB | 0.25 GB |
| Spectral indices, archive | hourly means, 128 bins × 3, uint8 | 365 days | 9 KB | 0.02 GB |
| Acoustic events | ≤ 2,000 events per day × ~48 B | 90 days | 96 KB | 0.04 GB |
| Band levels (live only) | 1 s, ~30 bands | 24 h in Kafka only | 8.6 MB | 0.04 GB |
| Weather, sun, GBIF context | hourly / daily / monthly | 365 days | < 2 KB | < 0.01 GB |
| BirdWeather context | ≤ 25 species × 24 hours × ~40 B per grid cell | 365 days | 24 KB | 0.04 GB |

With topic byte caps (~0.3 GB), the catalog (~0.1 GB) and the optional replay
corpus (≤ 0.15 GB), the total stays below about 1.7 GB, inside the default
2 GiB budget. Raw audio at rest from live sources: **0 bytes**, by design.

**Bandwidth** is the larger cost. A 128 kbit/s MP3 stream is about 1.4 GB per
day if listened to continuously. The default **dawn-weighted duty cycle**
(continuous from nautical dawn to three hours after sunrise, one minute in
five otherwise) listens to roughly a third of the day, about 0.46 GB per
stream per day.

## 9. References

- Alcocer, I., Lima, H., Sugai, L. S. M. & Llusia, D. (2022). Acoustic indices as proxies for biodiversity: a meta-analysis. *Biological Reviews*, 97(6), 2209–2236. <https://doi.org/10.1111/brv.12890>
- Boelman, N. T., Asner, G. P., Hart, P. J. & Martin, R. E. (2007). Multi-trophic invasion resistance in Hawaii: bioacoustics, field surveys, and airborne remote sensing. *Ecological Applications*, 17(8), 2137–2144.
- Bruni, A., Mennill, D. J. & Foote, J. R. (2014). Dawn chorus start time variation in a temperate bird community: relationships with seasonality, weather, and ambient light. *Journal of Ornithology*, 155, 877–890.
- Gibb, R., Browning, E., Glover-Kapfer, P. & Jones, K. E. (2019). Emerging opportunities and challenges for passive acoustics in ecological assessment and monitoring. *Methods in Ecology and Evolution*, 10(2), 169–185.
- Kasten, E. P., Gage, S. H., Fox, J. & Joo, W. (2012). The remote environmental assessment laboratory's acoustic library: an archive for studying soundscape ecology. *Ecological Informatics*, 12, 50–67.
- Metcalf, O. C., Lees, A. C., Barlow, J., Marsden, S. J. & Devenish, C. (2020). hardRain: an R package for quick, automated rainfall detection in ecoacoustic datasets using a threshold-based approach. *Ecological Indicators*, 109, 105793. <https://doi.org/10.1016/j.ecolind.2019.105793>
- Pieretti, N., Farina, A. & Morri, D. (2011). A new methodology to infer the singing activity of an avian community: the Acoustic Complexity Index (ACI). *Ecological Indicators*, 11(3), 868–873.
- Pijanowski, B. C. et al. (2011). Soundscape ecology: the science of sound in the landscape. *BioScience*, 61(3), 203–216.
- Saito, K. et al. (2015). Utilizing the Cyberforest live sound system with social media to remotely conduct woodland bird censuses in Central Japan. *Ambio*, 44(Suppl. 4), 572–583. <https://doi.org/10.1007/s13280-015-0708-y>
- Sethi, S. S., Ewers, R. M., Jones, N. S., Orme, C. D. L. & Picinali, L. (2018). Robust, real-time and autonomous monitoring of ecosystems with an open, low-cost, networked device. *Methods in Ecology and Evolution*, 9(12), 2383–2387. <https://doi.org/10.1111/2041-210X.13089>
- Sueur, J., Pavoine, S., Hamerlynck, O. & Duvail, S. (2008). Rapid acoustic survey for biodiversity appraisal. *PLoS ONE*, 3(12), e4065.
- Sugai, L. S. M., Silva, T. S. F., Ribeiro, J. W. & Llusia, D. (2019). Terrestrial passive acoustic monitoring: review and perspectives. *BioScience*, 69(1), 15–25.
- Towsey, M. (2017). *The calculation of acoustic indices derived from long-duration recordings of the natural environment.* QUT ePrints technical report.
- Towsey, M., Zhang, L., Cottman-Fields, M., Wimmer, J., Zhang, J. & Roe, P. (2014). Visualization of long-duration acoustic recordings of the environment. *Procedia Computer Science*, 29, 703–712.
- Towsey, M. et al. (2018). Long-duration, false-colour spectrograms for detecting species in large audio data-sets. *Journal of Ecoacoustics*, 2. <https://doi.org/10.22261/JEA.IUSWUI>
- Villanueva-Rivera, L. J., Pijanowski, B. C., Doucette, J. & Pekin, B. (2011). A primer of acoustic analysis for landscape ecologists. *Landscape Ecology*, 26, 1233–1246.

Tooling and data-source pages consulted on 2 November 2026:

- Locus Sonus soundmap and terms of use: <https://locusonus.org/soundmap/>
- xeno-canto API v3 documentation: <https://xeno-canto.org/explore/api>
- eBird API terms of use: <https://www.birds.cornell.edu/home/ebird-api-terms-of-use/>
- BirdWeather GraphQL API: <https://app.birdweather.com/api/>
- BirdWeather terms of service: <https://www.birdweather.com/terms-of-service>
- Orcasound node (live hydrophone streaming): <https://github.com/orcasound/orcanode>
- DuckLake 1.0 announcement: <https://ducklake.select/2026/04/13/ducklake-10/>
- Apache Kafka 4.2.0 release announcement: <https://kafka.apache.org/blog/2026/02/17/apache-kafka-4.2.0-release-announcement/>
- Dagster 1.12 release: <https://dagster.io/blog/dagster-1-12-monster-mash>
- ODCS v3.1.0 announcement: <https://bitol.io/bitol-announces-odcs-v3-1-0-stronger-smarter-and-stricter/>
- Soda Core release notes: <https://docs.soda.io/soda-v4/release-notes/soda-core-release-notes>
- Ingress NGINX retirement: <https://kubernetes.io/blog/2025/11/11/ingress-nginx-retirement/>
- dbt Python compatibility: <https://docs.getdbt.com/faqs/Core/install-python-compatibility>
- MinIO maintenance mode (coverage): <https://www.infoq.com/news/2025/12/minio-s3-api-alternatives/>
- Quix Streams: <https://pypi.org/project/quixstreams/>
