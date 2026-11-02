import io

import pytest

from tools.check_licences import (
    Policy,
    check,
    expression_allowed,
    licence_of,
    normalise_name,
    requirement_names,
)

ALLOWED = frozenset({"MIT", "BSD-3-Clause", "Apache-2.0", "BSD"})


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("MIT", True),
        ("GPL-3.0-only", False),
        ("MIT OR GPL-3.0-only", True),
        ("MIT AND GPL-3.0-only", False),
        ("MIT AND (Apache-2.0 OR GPL-3.0-only)", True),
        ("GPL-3.0-only OR MIT AND BSD-3-Clause", True),
        ("Apache-2.0 WITH LLVM-exception", True),
        ("Apache-2.0+", True),
    ],
)
def test_expression_allowed(expression: str, expected: bool) -> None:
    assert expression_allowed(expression, ALLOWED) is expected


@pytest.mark.parametrize("expression", ["(MIT", "MIT AND", "MIT MIT", ""])
def test_malformed_expression_is_rejected(expression: str) -> None:
    if expression:
        with pytest.raises(ValueError, match="licence expression"):
            expression_allowed(expression, ALLOWED)
    else:
        assert expression_allowed(expression, ALLOWED) is False


class FakeMetadata:
    def __init__(self, fields: dict[str, str], classifiers: list[str] | None = None) -> None:
        self._fields = fields
        self._classifiers = classifiers or []

    def get(self, key: str, default: str | None = None) -> str | None:
        return self._fields.get(key, default)

    def get_all(self, key: str) -> list[str] | None:
        return self._classifiers if key == "Classifier" else None


def test_licence_prefers_the_spdx_expression() -> None:
    meta = FakeMetadata({"License-Expression": "MIT", "License": "Apache-2.0"})
    assert licence_of(meta) == "MIT"  # type: ignore[arg-type]


def test_licence_falls_back_to_classifiers_when_license_is_full_text() -> None:
    meta = FakeMetadata(
        {"License": "Copyright (c) someone\nAll rights reserved ..."},
        ["License :: OSI Approved :: BSD License", "Programming Language :: Python"],
    )
    assert licence_of(meta) == "BSD"  # type: ignore[arg-type]


def test_licence_is_none_without_any_metadata() -> None:
    assert licence_of(FakeMetadata({})) is None  # type: ignore[arg-type]


def test_requirement_names_ignores_comments_options_and_markers() -> None:
    text = "# header\n-e ./local\nNumPy==2.5.4 ; python_version >= '3.13'\nscipy_extra.Thing>=1\n\n"
    assert requirement_names(io.StringIO(text)) == ["numpy", "scipy-extra-thing"]


def test_normalise_name() -> None:
    assert normalise_name("Typing_Extensions") == "typing-extensions"


def test_check_reports_unknown_and_excepted_packages() -> None:
    policy = Policy(allowed=ALLOWED, exceptions={"reviewed-pkg": "reviewed: dynamic LGPL linking"})
    findings = {f.name: f for f in check(["reviewed-pkg", "surely-not-installed-xyz"], policy)}
    assert findings["reviewed-pkg"].allowed
    assert not findings["surely-not-installed-xyz"].allowed
    assert findings["surely-not-installed-xyz"].note == "not installed"


def test_project_policy_loads_and_allows_mit() -> None:
    policy = Policy.from_pyproject()
    assert "MIT" in policy.allowed
    assert not {"GPL-3.0", "AGPL-3.0"} & policy.allowed
