# Project rules

Rules for anyone (person or coding assistant) changing this repository.
Every change must keep to them.

## Scope of the product

- **No AI or ML in the product.** No calls to model APIs (OpenAI, Anthropic,
  Gemini, Ollama, Hugging Face or others), no local models, embeddings or ML
  libraries (scikit-learn, PyTorch, TensorFlow, BirdNET and the like), and
  no datasets meant for training or evaluating models. Every value comes
  from documented, deterministic signal processing or statistics
  ([ADR 0002](docs/adr/0002-deterministic-signal-processing-without-machine-learning.md)).
- **No data sources whose content is produced by classifiers**, such as
  automated species-detection feeds.
- **No user accounts** and no storing of other people's data.
- **No security tooling that finds or exploits vulnerabilities** as part of
  the product.

## Data and privacy

- **No real personal data anywhere.** Fixtures, seed data, examples and
  screenshots use made-up, synthetic data. No scraping of data about people.
  No health or financial records.
- **Audio from live sources never leaves memory**: never write it to disk,
  logs, traces or test artefacts
  ([ADR 0003](docs/adr/0003-raw-audio-never-leaves-memory.md)).
- Drop fields that name or identify people at the connector; coarsen
  microphone coordinates to a 0.1° grid cell.
- Never commit data files (audio, Parquet, DuckDB, lake or cache files).
  Committed fixtures are small, synthetic and live in `tests/fixtures/`.
- Respect each source's terms, rate limits and attribution, as listed in
  [docs/data-sources.md](docs/data-sources.md). Add any new source there
  first.
- Stay within the storage budget
  ([ADR 0007](docs/adr/0007-storage-and-bandwidth-budgets-as-code.md)).

## Secrets

- No secrets in code or history. Read keys from environment variables, keep
  `.env` in `.gitignore`, and add each new variable to `.env.example` with a
  placeholder value.
- The gitleaks pre-commit hook must stay enabled.

## Git

- Commit after each working step with a clear Conventional Commit message
  (`feat:`, `fix:`, `docs:`, `chore:`, `test:`, `refactor:`, `ci:`).
- Never squash, amend or rebase pushed commits, never force-push, and never
  change commit dates.

## Documentation

- Keep README.md (what it does, who it's for, built with, how to run it)
  and ROADMAP.md up to date when a change affects them. Tick roadmap items
  when they are done and add a line to its progress log.
- Record significant decisions as ADRs in `docs/adr/`.

## Licensing

- The project is MIT-licensed (LICENSE in the top folder). Only add
  dependencies whose licences allow that, and never copy code we don't have
  the right to share.

## Engineering conventions

- Python 3.13 baseline, managed with uv; Ruff for linting and formatting;
  mypy `--strict`; pytest with Hypothesis.
- Follow the definition of done in [ROADMAP.md](ROADMAP.md#7-definition-of-done).
