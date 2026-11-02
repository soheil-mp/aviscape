"""Shared pytest configuration for every package in the workspace."""

import os

from hypothesis import HealthCheck, settings

# `dev` keeps the local loop fast; `ci` explores more and is reproducible.
settings.register_profile("dev", max_examples=50)
settings.register_profile(
    "ci",
    max_examples=500,
    derandomize=True,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
    print_blob=True,
)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "dev"))
