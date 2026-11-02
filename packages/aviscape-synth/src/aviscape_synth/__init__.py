"""Seeded synthetic soundscapes and a replay simulator for testing."""

from aviscape_synth.source import (
    DEFAULT_SAMPLE_RATE,
    DEFAULT_WINDOW_S,
    AudioWindow,
    Tone,
    ToneNoiseSource,
)

__all__ = [
    "DEFAULT_SAMPLE_RATE",
    "DEFAULT_WINDOW_S",
    "AudioWindow",
    "Tone",
    "ToneNoiseSource",
    "__version__",
]

__version__ = "0.0.0"
