"""Check that every shipped dependency has a licence on the allow-list.

Reads requirement lines (as printed by ``uv export --no-dev``) from a file or
standard input, looks up each distribution's licence in the installed
environment, and fails if any licence is not allowed. The allow-list and
reviewed exceptions live in ``pyproject.toml`` under
``[tool.aviscape.licences]``.

Licence information is taken, in order of preference, from the PEP 639
``License-Expression`` field, a short ``License`` field, or the
``License ::`` trove classifiers.

Run it with ``just licences``, which pipes ``uv export`` into
``python -m tools.check_licences -``.
"""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import TextIO

PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"

# Trove classifiers mapped to SPDX identifiers. Families without a precise
# identifier map to a family name that the allow-list can include.
CLASSIFIER_TO_SPDX: dict[str, str] = {
    "License :: OSI Approved :: MIT License": "MIT",
    "License :: OSI Approved :: MIT No Attribution License (MIT-0)": "MIT-0",
    "License :: OSI Approved :: BSD License": "BSD",
    "License :: OSI Approved :: Apache Software License": "Apache-2.0",
    "License :: OSI Approved :: ISC License (ISCL)": "ISC",
    "License :: OSI Approved :: Python Software Foundation License": "PSF-2.0",
    "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)": "MPL-2.0",
    "License :: OSI Approved :: zlib/libpng License": "Zlib",
    "License :: OSI Approved :: The Unlicense (Unlicense)": "Unlicense",
    "License :: CC0 1.0 Universal (CC0 1.0) Public Domain Dedication": "CC0-1.0",
    "License :: OSI Approved :: GNU General Public License v2 (GPLv2)": "GPL-2.0",
    "License :: OSI Approved :: GNU General Public License v3 (GPLv3)": "GPL-3.0",
    "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)": "LGPL-3.0",
    "License :: OSI Approved :: GNU Affero General Public License v3": "AGPL-3.0",
}

_TOKEN = re.compile(r"\(|\)|[A-Za-z0-9.+:-]+")
_MAX_SHORT_LICENSE = 40


@dataclass(frozen=True, slots=True)
class Policy:
    """Which licences are allowed, and reviewed per-package exceptions."""

    allowed: frozenset[str]
    exceptions: dict[str, str]

    @classmethod
    def from_pyproject(cls, path: Path = PYPROJECT) -> Policy:
        """Load the policy from ``[tool.aviscape.licences]``."""
        config = tomllib.loads(path.read_text())["tool"]["aviscape"]["licences"]
        return cls(
            allowed=frozenset(config["allowed"]),
            exceptions={normalise_name(k): v for k, v in config.get("exceptions", {}).items()},
        )


@dataclass(frozen=True, slots=True)
class Finding:
    """The licence verdict for one distribution."""

    name: str
    licence: str | None
    allowed: bool
    note: str = ""


def normalise_name(name: str) -> str:
    """Normalise a distribution name as in PEP 503."""
    return re.sub(r"[-_.]+", "-", name).lower()


def expression_allowed(expression: str, allowed: frozenset[str]) -> bool:
    """Evaluate an SPDX licence expression against the allow-list.

    ``A OR B`` is allowed if either side is; ``A AND B`` only if both are.
    ``X WITH exception`` is judged by ``X``. ``AND`` binds tighter than ``OR``.
    """
    tokens: list[str] = _TOKEN.findall(expression)
    if not tokens:
        return False
    position = 0

    def peek() -> str | None:
        return tokens[position] if position < len(tokens) else None

    def take() -> str:
        nonlocal position
        if position >= len(tokens):
            msg = f"unexpected end of licence expression: {expression!r}"
            raise ValueError(msg)
        token = tokens[position]
        position += 1
        return token

    def parse_or() -> bool:
        result = parse_and()
        while peek() == "OR":
            take()
            right = parse_and()
            result = result or right
        return result

    def parse_and() -> bool:
        result = parse_atom()
        while peek() == "AND":
            take()
            right = parse_atom()
            result = result and right
        return result

    def parse_atom() -> bool:
        symbol = take()
        if symbol == "(":
            result = parse_or()
            if take() != ")":
                msg = f"unbalanced parentheses in licence expression: {expression!r}"
                raise ValueError(msg)
            return result
        if peek() == "WITH":
            take()
            take()  # the exception identifier does not change the verdict
        return symbol.removesuffix("+") in allowed

    result = parse_or()
    if position != len(tokens):
        msg = f"trailing tokens in licence expression: {expression!r}"
        raise ValueError(msg)
    return result


def licence_of(meta: metadata.PackageMetadata) -> str | None:
    """Return the best available licence description for a distribution."""
    expression = meta.get("License-Expression")
    if expression:
        return expression.strip()
    short = (meta.get("License") or "").strip()
    if short and "\n" not in short and len(short) <= _MAX_SHORT_LICENSE:
        return short
    classifiers = [
        CLASSIFIER_TO_SPDX.get(c, c.rsplit(" :: ", 1)[-1])
        for c in meta.get_all("Classifier") or []
        if c.startswith("License ::")
    ]
    return " OR ".join(sorted(set(classifiers))) or None


def requirement_names(lines: TextIO) -> list[str]:
    """Extract distribution names from ``requirements.txt``-style lines."""
    names = []
    for raw in lines:
        line = raw.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        match = re.match(r"[A-Za-z0-9][A-Za-z0-9._-]*", line)
        if match:
            names.append(normalise_name(match.group(0)))
    return names


def check(names: list[str], policy: Policy) -> list[Finding]:
    """Judge every named distribution against the policy."""
    findings = []
    for name in names:
        if name in policy.exceptions:
            findings.append(Finding(name, None, allowed=True, note=policy.exceptions[name]))
            continue
        try:
            licence = licence_of(metadata.metadata(name))
        except metadata.PackageNotFoundError:
            findings.append(Finding(name, None, allowed=False, note="not installed"))
            continue
        if licence is None:
            findings.append(Finding(name, None, allowed=False, note="no licence metadata"))
            continue
        try:
            ok = expression_allowed(licence, policy.allowed)
        except ValueError as error:
            findings.append(Finding(name, licence, allowed=False, note=str(error)))
            continue
        findings.append(Finding(name, licence, allowed=ok))
    return findings


def main(argv: list[str] | None = None) -> int:
    """Run the check and print a report; return a process exit code."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "requirements",
        type=argparse.FileType("r"),
        help="requirements file, or - for standard input",
    )
    args = parser.parse_args(argv)
    findings = check(requirement_names(args.requirements), Policy.from_pyproject())
    for finding in findings:
        status = "ok  " if finding.allowed else "FAIL"
        detail = finding.licence or "-"
        note = f"  ({finding.note})" if finding.note else ""
        print(f"{status} {finding.name}: {detail}{note}")
    failures = [f for f in findings if not f.allowed]
    print(f"{len(findings)} distributions checked, {len(failures)} not allowed.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
