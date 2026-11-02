# Contributing to aviscape

Thanks for your interest. This guide explains how to set up the project, how
work is planned, and what a change needs before it is merged.

## Ground rules

These are non-negotiable, because they define what the project is:

- **No machine learning in the product**: no models, inference, embeddings or
  ML libraries, and no datasets for training or evaluating models
  ([ADR 0002](docs/adr/0002-deterministic-signal-processing-without-machine-learning.md)).
- **No audio at rest from live sources, and no personal data anywhere**
  ([ADR 0003](docs/adr/0003-raw-audio-never-leaves-memory.md)). Test fixtures
  and examples are synthetic.
- **Respect every data source's terms**, as listed in
  [docs/data-sources.md](docs/data-sources.md).
- **No secrets in the repository.** Configuration comes from environment
  variables; add new ones to `.env.example` with a placeholder.

Everyone taking part follows the [Code of Conduct](CODE_OF_CONDUCT.md).

## Set up

You need [uv](https://docs.astral.sh/uv/), [just](https://just.systems/)
(`uv tool install rust-just`) and Git.

```sh
git clone https://github.com/soheil-mp/aviscape.git
cd aviscape
just setup   # locked environment and git hooks
just check   # what CI runs: lint, strict types, tests and coverage gates
```

The repository is a uv workspace. Each package lives in `packages/<name>/`
with its code in `src/` and its tests in `tests/`.

## How work is planned

- The [roadmap](ROADMAP.md) lists every planned work item with a stable ID
  (for example `M2.6`), an estimate and an acceptance test.
- Each item becomes an issue titled `M2.6: <short description>`. Pick an open
  one, or open a new issue first for anything not on the roadmap.
- Significant decisions (a new runtime dependency, data source, guarantee or
  budget) get an [architecture decision record](docs/adr/) in the same pull
  request.

## Making a change

1. Branch from `main`: `git switch -c m2.6-aci`.
2. Write the test first where you can. DSP code is checked against analytic
   expectations and properties (Hypothesis), not just examples.
3. Run `just check` before you push. The hooks also run on every commit.
4. Use [Conventional Commits](https://www.conventionalcommits.org/) for
   commit messages and pull request titles (`feat(dsp): add ACI`). The
   commit-msg hook enforces it; release notes are generated from them.
5. Open a pull request and fill in the template. CI must be green.

Never rewrite history that has been pushed: no force-pushes, no squashing or
amending of pushed commits.

## Definition of done

A change is done when it meets the
[definition of done](ROADMAP.md#7-definition-of-done): formatted, linted,
strictly typed, tested to the coverage gates, documented, with contracts,
observability and data-quality checks where they apply, and the roadmap item
ticked.

## Reporting bugs and security issues

Use the issue forms for bugs and ideas. Report security issues privately as
described in [SECURITY.md](SECURITY.md), never in a public issue.
