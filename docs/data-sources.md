# Data sources and licence register

Every external source the platform reads, what it takes, under which terms,
and how personal data is kept out. Terms were read on **2 November 2026** and
are reviewed every quarter (roadmap item M10.7). A connector whose terms
change is switched off by configuration until it is reviewed again.

**Ground rules for all sources**

1. **Features, not recordings.** Audio from live sources is decoded and
   analysed in memory and never written to disk, logs or traces
   ([ADR 0003](adr/0003-raw-audio-never-leaves-memory.md)).
2. **No personal data.** Fields that name or identify a person are dropped at
   the connector, before anything reaches Kafka. Coordinates of microphones
   are coarsened to a 0.1° grid cell (about 11 km north–south).
3. **No redistribution of third-party data.** Downloaded and derived data
   stay in the local lake; only synthetic data is committed to git or used in
   the public demo.
4. **Polite clients.** Every HTTP client has a rate limit, retries with
   backoff, caching, and a descriptive `User-Agent` that links to this
   repository.

## Register

| Source | Used for | Access | Terms (summary) | Personal data handling | Default |
| :-- | :-- | :-- | :-- | :-- | :-- |
| [Locus Sonus Locustream](https://locusonus.org/soundmap/) | live audio from open microphones; list of active streams | Icecast MP3/Ogg; JSON list, no key | free and open use, including recording and adapting; users must cite Locus Sonus; the user is responsible for third-party complaints | `artist` (a person's name) dropped; coordinates coarsened; audio in memory only | on, allow-list of up to 5 streams |
| Own microphone | live audio from a microphone you control | ALSA/PortAudio, local | yours | same as above; placement guide avoids homes and paths | off |
| Synthetic soundscape generator | tests, demo, load and chaos testing | local code | MIT (this repository) | none: fully synthetic | on |
| [xeno-canto API v3](https://xeno-canto.org/explore/api) | optional replay corpus of bird recordings | personal API key in `XENO_CANTO_API_KEY` | key must not be shared or published; per-recording Creative Commons licence | recordist names not stored; only catalogue number, licence URL and species kept; NoDerivatives licences excluded; audio never redistributed; cache capped at 150 MB and kept outside git | off |
| [Open-Meteo](https://open-meteo.com/) | hourly precipitation, wind, temperature, cloud cover; historical archive | REST, no key | free for non-commercial use, data under CC BY 4.0; attribution required; fewer than about 10,000 calls per day | queried by coarse grid cell only | on |
| [GBIF](https://www.gbif.org/) occurrence API | monthly counts of bird species recorded near each sensor, as context | REST, no key | data licences vary per dataset (CC0, CC BY, CC BY-NC); cite GBIF.org with the query date | facet counts only (no record-level data, no recorder names) | on |
| Sun and moon positions | civil, nautical and astronomical twilight, sunrise, sunset | computed locally (`astral` library, Apache-2.0) | n/a | n/a | on |
| OpenStreetMap basemap (dashboard) | map background | self-hosted PMTiles extract, no third-party tile server | ODbL; "© OpenStreetMap contributors" | n/a | on |

## Attribution text

Shown in the dashboard footer, the API's `/v1/about` response and the docs:

> Live sounds: Locus Sonus – Locustream open microphones (www.locusonus.org).
> Weather data by Open-Meteo.com (CC BY 4.0).
> Species context: GBIF.org, occurrence search, accessed on the date shown.
> Map data © OpenStreetMap contributors.

When the optional xeno-canto corpus is used, each derived result links to
the recording page (`https://xeno-canto.org/<catalogue number>`), which
carries the recordist's attribution and licence.

## Considered and not used

| Source | Why not |
| :-- | :-- |
| BirdWeather and similar detection feeds | detections come from a machine-learning classifier; every signal in this platform is produced by documented, deterministic methods ([ADR 0002](adr/0002-deterministic-signal-processing-without-machine-learning.md)) |
| eBird API 2.0 | needs a key; non-commercial licence that limits sharing with third parties; kept as an open question in the roadmap |
| Cyberforest archive (University of Tokyo) | no standard open licence found for the archive; would need permission |
| Locus Sonus streams outside the allow-list | most are urban or underwater; the allow-list keeps bandwidth and relevance under control |

## Stream catalogue fields

What the Locus Sonus connector keeps from each entry of the active-stream
list (checked 2 November 2026; 11 fields per entry):

| Field | Kept | As |
| :-- | :-- | :-- |
| `id` | yes | `source_stream_id` |
| `name` | yes | `stream_name` (place-based) |
| `url` | yes | `stream_url` |
| `ext` | yes | `codec` |
| `lat`, `lng` | coarsened | `geocell_lat`, `geocell_lon` (0.1° grid) |
| `city`, `country` | yes | `city`, `country` |
| `artist` | **no** | dropped at the connector |
| `source`, `link` | yes | provenance |
