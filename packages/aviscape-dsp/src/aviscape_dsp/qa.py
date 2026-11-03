"""Signal quality metrics: is this audio fit to compute indices from?

Each metric targets one fault that live streams and cheap microphones produce:

=====================  ===============================================================
Metric                 Fault it reveals
=====================  ===============================================================
``clipping_ratio``     Gain set too high: samples pinned at full scale
``dc_offset``          A biased microphone or ADC: the signal's mean is not zero
``peak_dbfs``          Headroom: how close the loudest sample comes to full scale
``rms_dbfs``           Overall level, from :mod:`aviscape_dsp.levels`
``crest_factor_db``    Peak-to-RMS ratio: very low means heavy limiting or clipping,
                       very high means isolated spikes in near-silence
``silence``            Digital silence: runs of exact zeros (muted input, dead stream)
``dropouts``           Short holds: runs of one repeated value that is not silence
                       (buffer underruns, stuck converters)
=====================  ===============================================================

Peak levels use full scale (a sample of ±1.0) as 0 dBFS; RMS levels follow AES17, so a
full-scale sine reads 0 dBFS on both. The thresholds are this package's defaults, chosen to
be conservative; they are parameters, not constants.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

from aviscape_dsp.levels import rms, rms_dbfs

CLIP_THRESHOLD = 0.999
"""Absolute sample value at or above which a sample counts as clipped (about -0.009 dBFS)."""

MIN_SILENCE_S = 0.1
"""Shortest run of exact zeros reported as digital silence."""

MIN_DROPOUT_S = 0.002
"""Shortest run of one repeated sample value reported as a dropout."""


@dataclass(frozen=True, slots=True)
class Run:
    """A run of samples: ``start`` index and ``length`` in samples."""

    start: int
    length: int


@dataclass(frozen=True, slots=True)
class SignalQuality:
    """Every quality metric of one window.

    Attributes:
        clipping_ratio: Fraction of samples at or above the clip threshold, in [0, 1].
        dc_offset: Mean of the samples, in full-scale units.
        peak_dbfs: Largest absolute sample in dBFS (``-inf`` for digital silence).
        rms_dbfs: RMS level in dBFS, AES17 (``-inf`` for digital silence).
        crest_factor_db: Peak over RMS in dB (``nan`` for digital silence).
        silence_ratio: Fraction of samples inside digital-silence runs.
        silence_runs: Number of digital-silence runs.
        dropout_runs: Number of dropouts.
    """

    clipping_ratio: float
    dc_offset: float
    peak_dbfs: float
    rms_dbfs: float
    crest_factor_db: float
    silence_ratio: float
    silence_runs: int
    dropout_runs: int


def _signal(samples: ArrayLike) -> NDArray[np.float64]:
    signal = np.asarray(samples, dtype=np.float64)
    if signal.ndim != 1 or signal.size == 0:
        msg = f"expected a non-empty one-dimensional signal, got shape {signal.shape}"
        raise ValueError(msg)
    return signal


def clipping_ratio(samples: ArrayLike, *, threshold: float = CLIP_THRESHOLD) -> float:
    """Fraction of samples whose absolute value is at least ``threshold``."""
    signal = _signal(samples)
    return float(np.count_nonzero(np.abs(signal) >= threshold) / signal.size)


def dc_offset(samples: ArrayLike) -> float:
    """Mean of the samples in full-scale units."""
    return float(_signal(samples).mean())


def peak_dbfs(samples: ArrayLike) -> float:
    """Largest absolute sample in dBFS, where a sample of ±1.0 is 0 dBFS."""
    peak = float(np.abs(_signal(samples)).max())
    return 20 * math.log10(peak) if peak > 0 else -math.inf


def crest_factor_db(samples: ArrayLike) -> float:
    """Peak-to-RMS ratio in dB: 3.01 dB for a sine, 0 dB for a square wave.

    Returns ``nan`` for digital silence, where the ratio is undefined.
    """
    signal = _signal(samples)
    level = rms(signal)
    if level == 0:
        return math.nan
    return 20 * math.log10(float(np.abs(signal).max()) / level)


def constant_runs(samples: ArrayLike, min_length: int) -> list[Run]:
    """Runs of at least ``min_length`` consecutive identical samples, in order."""
    signal = _signal(samples)
    if min_length < 1:
        msg = f"min_length must be at least 1, got {min_length}"
        raise ValueError(msg)
    change = np.flatnonzero(np.diff(signal) != 0) + 1
    starts = np.concatenate(([0], change))
    lengths = np.diff(np.concatenate((starts, [signal.size])))
    keep = lengths >= min_length
    return [Run(int(s), int(n)) for s, n in zip(starts[keep], lengths[keep], strict=True)]


def silence_runs(
    samples: ArrayLike, sample_rate: int, *, min_duration_s: float = MIN_SILENCE_S
) -> list[Run]:
    """Runs of exact zeros lasting at least ``min_duration_s``."""
    signal = _signal(samples)
    min_length = max(1, math.ceil(min_duration_s * sample_rate))
    return [r for r in constant_runs(signal, min_length) if signal[r.start] == 0]


def dropouts(
    samples: ArrayLike,
    sample_rate: int,
    *,
    min_duration_s: float = MIN_DROPOUT_S,
    min_silence_s: float = MIN_SILENCE_S,
) -> list[Run]:
    """Holds of one repeated value lasting at least ``min_duration_s`` that are not silence.

    A run of zeros long enough to count as digital silence is reported by
    :func:`silence_runs` instead; shorter zero runs and runs of any other repeated value are
    dropouts. Audio with real content almost never repeats a sample value for 2 ms.
    """
    signal = _signal(samples)
    min_length = max(2, math.ceil(min_duration_s * sample_rate))
    silence_length = max(1, math.ceil(min_silence_s * sample_rate))
    return [
        r
        for r in constant_runs(signal, min_length)
        if signal[r.start] != 0 or r.length < silence_length
    ]


def assess(samples: ArrayLike, sample_rate: int) -> SignalQuality:
    """Compute every quality metric of one window with the default thresholds."""
    signal = _signal(samples)
    silent = silence_runs(signal, sample_rate)
    return SignalQuality(
        clipping_ratio=clipping_ratio(signal),
        dc_offset=dc_offset(signal),
        peak_dbfs=peak_dbfs(signal),
        rms_dbfs=rms_dbfs(signal),
        crest_factor_db=crest_factor_db(signal),
        silence_ratio=sum(r.length for r in silent) / signal.size,
        silence_runs=len(silent),
        dropout_runs=len(dropouts(signal, sample_rate)),
    )
