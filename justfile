# Task runner for aviscape. Run `just` to list the recipes.
# Requires uv (https://docs.astral.sh/uv/) and just (https://just.systems/).

set shell := ["bash", "-euo", "pipefail", "-c"]

uv := "uv run --frozen"

# List the available recipes.
default:
    @just --list --unsorted

# Install the locked environment and the git hooks.
setup:
    uv sync --locked
    uvx pre-commit install --install-hooks

# Lint and check formatting without changing files.
lint:
    {{ uv }} ruff check .
    {{ uv }} ruff format --check .

# Apply safe lint fixes and format the code.
fmt:
    {{ uv }} ruff check --fix .
    {{ uv }} ruff format .

# Type-check every package with mypy in strict mode.
typecheck:
    {{ uv }} mypy

# Run the tests in parallel (pass extra pytest arguments after the recipe name).
test *args:
    {{ uv }} pytest -n auto {{ args }}

# Run the tests with branch coverage and enforce the coverage gates.
cov:
    {{ uv }} pytest -n auto --cov --cov-report=term --cov-report=xml
    {{ uv }} coverage report --include="*/aviscape_dsp/*" --fail-under=90

# Run every check that CI runs on a pull request.
check: lint typecheck cov

# Run all pre-commit hooks against every file.
hooks:
    uvx pre-commit run --all-files

# Remove caches and build output.
clean:
    rm -rf .pytest_cache .mypy_cache .ruff_cache .hypothesis htmlcov coverage.xml .coverage .coverage.* dist build
