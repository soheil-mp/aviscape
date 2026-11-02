"""A seeded tone-plus-noise source that emits fixed-length audio windows.

This is the synthetic sensor of the walking skeleton: deterministic, privacy
free and cheap. The same seed always produces byte-identical audio, so tests
and demos can assert exact downstream values. Richer soundscapes (bird-like
calls, rain, wind, faults) arrive with roadmap milestone M3.
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np
from numpy.typing import NDArray

DEFAULT_SAMPLE_RATE = 22_050
"""Hz. Matches the analysis rate of the DSP library (Nyquist 11.025 kHz)."""

DEFAULT_WINDOW_S = 60
"""Seconds per window: one window becomes one row of minute-level features."""


@dataclass(frozen=True, slots=True)
class Tone:
    """A sinusoid with a peak amplitude relative to digital full scale (1.0)."""

    frequency_hz: float
    amplitude: float

    def __post_init__(self) -> None:
        """Reject non-positive frequencies and amplitudes outside [0, 1]."""
        if not self.frequency_hz > 0:
            msg = f"frequency_hz must be positive, got {self.frequency_hz}"
            raise ValueError(msg)
        if not 0 <= self.amplitude <= 1:
            msg = f"amplitude must be within [0, 1], got {self.amplitude}"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class AudioWindow:
    """A fixed-length block of mono audio and when it started.

    Attributes:
        sensor_id: Identifier of the (virtual) sensor that produced it.
        start: Start of the window, timezone-aware and aligned to the window
            length (for 60 s windows: a UTC minute boundary).
        sample_rate: Samples per second.
        samples: Mono float32 samples, nominally within [-1, 1]. Values are not
            clipped; clipping is a quality problem for the DSP to detect.
    """

    sensor_id: str
    start: datetime
    sample_rate: int
    samples: NDArray[np.float32]

    @property
    def duration_s(self) -> float:
        """Length of the window in seconds."""
        return self.samples.size / self.sample_rate


@dataclass(frozen=True, slots=True)
class ToneNoiseSource:
    """Sum of sinusoids plus Gaussian white noise, cut into aligned windows.

    Tones are phase-continuous across windows, so consecutive windows join
    without discontinuities. Noise for window ``i`` is drawn from a generator
    seeded with ``(seed, i)``, so any window can be regenerated on its own.

    Attributes:
        sensor_id: Identifier attached to every window.
        seed: Non-negative seed for the noise generator.
        start: Start of window 0; timezone-aware and aligned to ``window_s``.
        tones: Sinusoids to sum; their amplitudes may add up to at most 1.
        noise_rms: Standard deviation of the white noise (full scale = 1).
        sample_rate: Samples per second.
        window_s: Window length in whole seconds.
    """

    sensor_id: str
    seed: int
    start: datetime
    tones: tuple[Tone, ...] = ()
    noise_rms: float = 0.0
    sample_rate: int = DEFAULT_SAMPLE_RATE
    window_s: int = DEFAULT_WINDOW_S

    def __post_init__(self) -> None:
        """Validate the configuration so every window is well defined."""
        if self.seed < 0:
            msg = f"seed must be non-negative, got {self.seed}"
            raise ValueError(msg)
        if self.sample_rate <= 0 or self.window_s <= 0:
            msg = "sample_rate and window_s must be positive"
            raise ValueError(msg)
        if self.start.tzinfo is None or self.start.utcoffset() is None:
            msg = "start must be timezone-aware"
            raise ValueError(msg)
        if self.start.timestamp() % self.window_s != 0:
            msg = f"start must be aligned to a {self.window_s} s boundary, got {self.start}"
            raise ValueError(msg)
        nyquist = self.sample_rate / 2
        for tone in self.tones:
            if tone.frequency_hz >= nyquist:
                msg = f"tone at {tone.frequency_hz} Hz is not below Nyquist ({nyquist} Hz)"
                raise ValueError(msg)
        if math.fsum(tone.amplitude for tone in self.tones) > 1:
            msg = "tone amplitudes must add up to at most 1 (full scale)"
            raise ValueError(msg)
        if self.noise_rms < 0:
            msg = f"noise_rms must be non-negative, got {self.noise_rms}"
            raise ValueError(msg)

    @property
    def samples_per_window(self) -> int:
        """Number of samples in each window."""
        return self.sample_rate * self.window_s

    def window(self, index: int) -> AudioWindow:
        """Generate window ``index`` (0-based) independently of the others."""
        if index < 0:
            msg = f"index must be non-negative, got {index}"
            raise ValueError(msg)
        n = self.samples_per_window
        t = (np.arange(n, dtype=np.float64) + index * n) / self.sample_rate
        signal = np.zeros(n, dtype=np.float64)
        for tone in self.tones:
            signal += tone.amplitude * np.sin(2 * np.pi * tone.frequency_hz * t)
        if self.noise_rms > 0:
            rng = np.random.default_rng([self.seed, index])
            signal += rng.normal(0.0, self.noise_rms, n)
        return AudioWindow(
            sensor_id=self.sensor_id,
            start=self.start + timedelta(seconds=index * self.window_s),
            sample_rate=self.sample_rate,
            samples=signal.astype(np.float32),
        )

    def windows(
        self,
        count: int | None = None,
        *,
        speed: float | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> Iterator[AudioWindow]:
        """Yield consecutive windows, optionally paced against the wall clock.

        Args:
            count: Number of windows to yield; ``None`` yields forever.
            speed: ``None`` yields as fast as possible; ``1.0`` paces windows in
                real time; ``60.0`` replays one hour per minute.
            sleep: Function used for pacing (injected in tests).
        """
        if speed is not None and not speed > 0:
            msg = f"speed must be positive, got {speed}"
            raise ValueError(msg)
        index = 0
        while count is None or index < count:
            if speed is not None and index > 0:
                sleep(self.window_s / speed)
            yield self.window(index)
            index += 1
