"""Acoustic indices.

Each index documents its definition, defaults and source. More indices arrive
with roadmap milestone M2.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.signal import hilbert

from aviscape_dsp.spectrum import Spectrogram

NDSI_ANTHROPHONY_HZ = (1_000.0, 2_000.0)
"""Default anthrophony band, after Kasten et al. (2012)."""

NDSI_BIOPHONY_HZ = (2_000.0, 11_000.0)
"""Default biophony band, after Kasten et al. (2012)."""


def ndsi(
    spec: Spectrogram,
    *,
    anthrophony_hz: tuple[float, float] = NDSI_ANTHROPHONY_HZ,
    biophony_hz: tuple[float, float] = NDSI_BIOPHONY_HZ,
) -> float:
    """Normalised Difference Soundscape Index.

    ``NDSI = (B - A) / (B + A)``, where ``A`` and ``B`` are the powers in the
    anthrophony and biophony bands of the frame-averaged spectrum. Values lie
    in [-1, 1]: +1 means all energy is in the biophony band, -1 all in the
    anthrophony band. The index is independent of overall gain.

    Reference: Kasten, E. P., Gage, S. H., Fox, J. & Joo, W. (2012). The remote
    environmental assessment laboratory's acoustic library: an archive for
    studying soundscape ecology. *Ecological Informatics*, 12, 50-67.

    Args:
        spec: Spectrogram of the window.
        anthrophony_hz: Half-open band ``[low, high)`` for anthrophony.
        biophony_hz: Half-open band ``[low, high)`` for biophony.

    Returns:
        The index, or ``nan`` when both bands are silent.

    Raises:
        ValueError: If a band is empty, inverted, or starts above Nyquist.
    """
    nyquist = spec.sample_rate / 2
    for name, (low, high) in (("anthrophony", anthrophony_hz), ("biophony", biophony_hz)):
        if low >= nyquist:
            msg = f"{name} band starts at {low} Hz, above Nyquist ({nyquist} Hz)"
            raise ValueError(msg)
        if not 0 <= low < high:
            msg = f"{name} band must satisfy 0 <= low < high, got [{low}, {high})"
            raise ValueError(msg)
    anthrophony = spec.band_power(*anthrophony_hz)
    biophony = spec.band_power(*biophony_hz)
    total = anthrophony + biophony
    if total == 0:
        return math.nan
    return (biophony - anthrophony) / total


def _normalised_entropy(weights: NDArray[np.float64]) -> float:
    """Shannon entropy of non-negative weights, divided by its maximum ``log(n)``.

    Returns ``nan`` when all weights are zero or there is only one weight.
    """
    total = float(weights.sum())
    if total == 0 or weights.size < 2:  # noqa: PLR2004 - entropy needs two outcomes
        return math.nan
    p = weights[weights > 0] / total
    return float(-(p * np.log(p)).sum() / math.log(weights.size))


def temporal_entropy(samples: ArrayLike) -> float:
    """Temporal entropy ``Ht`` of the amplitude envelope (Sueur et al., 2008).

    The envelope is the magnitude of the analytic signal (Hilbert transform). Treated as a
    probability mass over time, its Shannon entropy is divided by ``log(n)`` for ``n``
    samples, so ``Ht`` lies in [0, 1]: near 1 for a steady envelope (constant noise or a
    tone), lower when the energy sits in a few short events. The scale is logarithmic: energy
    confined to a fraction ``f`` of the samples gives about ``log(f * n) / log(n)``, so even
    1 % of a ten-second window scores about 0.65.

    Reference: Sueur, J., Pavoine, S., Hamerlynck, O. & Duvail, S. (2008). Rapid acoustic
    survey for biodiversity appraisal. *PLoS ONE*, 3(12), e4065.

    Returns:
        ``Ht``, or ``nan`` for digital silence.
    """
    signal = np.asarray(samples, dtype=np.float64)
    if signal.ndim != 1:
        msg = f"samples must be one-dimensional, got shape {signal.shape}"
        raise ValueError(msg)
    envelope = np.abs(np.asarray(hilbert(signal)))
    return _normalised_entropy(envelope)


def spectral_entropy(spec: Spectrogram) -> float:
    """Spectral entropy ``Hf`` of the mean amplitude spectrum (Sueur et al., 2008).

    The mean amplitude spectrum (the square root of each frame's PSD, averaged over frames) is
    treated as a probability mass over frequency bins; its Shannon entropy is divided by
    ``log(n_bins)``. ``Hf`` lies in [0, 1]: near 1 for white noise, low for a pure tone.

    Returns:
        ``Hf``, or ``nan`` for digital silence.
    """
    amplitude = np.sqrt(spec.psd).mean(axis=0)
    return _normalised_entropy(np.asarray(amplitude, dtype=np.float64))


def acoustic_entropy(samples: ArrayLike, spec: Spectrogram) -> float:
    """Acoustic entropy ``H = Ht * Hf`` (Sueur et al., 2008), in [0, 1]."""
    return temporal_entropy(samples) * spectral_entropy(spec)


@dataclass(frozen=True, slots=True)
class AcousticComplexity:
    """Acoustic Complexity Index of a window.

    Attributes:
        total: Sum of the per-bin values over all frequency bins.
        per_bin: ACI of each frequency bin, shape ``(n_bins,)``; ``0`` for silent bins.
        chunks: Number of temporal chunks the window was split into.
    """

    total: float
    per_bin: NDArray[np.float64]
    chunks: int


def acoustic_complexity(spec: Spectrogram, *, chunk_s: float | None = None) -> AcousticComplexity:
    """Acoustic Complexity Index (Pieretti et al., 2011).

    For every frequency bin and every temporal chunk, ACI is the summed absolute change in
    intensity between neighbouring frames divided by the summed intensity:

    ``ACI(bin, chunk) = sum_k |I[k + 1] - I[k]| / sum_k I[k]``

    The per-bin value adds up the chunks, and the total adds up the bins. Intensity is the
    amplitude spectrum (the square root of the PSD). Steady sounds (a constant tone, an engine
    hum) score near zero however loud they are; sounds whose intensity changes from frame to
    frame, such as song, score high. Like the original, the index depends on frame length and
    chunk length, so those must be reported with it.

    Reference: Pieretti, N., Farina, A. & Morri, D. (2011). A new methodology to infer the
    singing activity of an avian community: the Acoustic Complexity Index (ACI). *Ecological
    Indicators*, 11(3), 868-873.

    Args:
        spec: Spectrogram of the window, with at least two frames per chunk.
        chunk_s: Length of a temporal chunk in seconds; ``None`` uses the whole window as one
            chunk. Trailing frames that do not fill a chunk are dropped.

    Raises:
        ValueError: If a chunk would hold fewer than two frames.
    """
    hop_s = spec.hop_length / spec.sample_rate
    frames_per_chunk = spec.n_frames if chunk_s is None else math.floor(chunk_s / hop_s + 1e-9)
    if frames_per_chunk < 2 or frames_per_chunk > spec.n_frames:  # noqa: PLR2004 - a change needs two frames
        msg = (
            f"a chunk must hold between 2 and {spec.n_frames} frames, "
            f"got {frames_per_chunk} (chunk_s={chunk_s}, hop {hop_s:.4f} s)"
        )
        raise ValueError(msg)
    chunks = spec.n_frames // frames_per_chunk
    intensity = np.sqrt(spec.psd[: chunks * frames_per_chunk])
    blocks = intensity.reshape(chunks, frames_per_chunk, -1)
    change = np.abs(np.diff(blocks, axis=1)).sum(axis=1)
    total = blocks.sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        per_chunk = np.where(total > 0, change / total, 0.0)
    per_bin = np.asarray(per_chunk.sum(axis=0), dtype=np.float64)
    return AcousticComplexity(total=float(per_bin.sum()), per_bin=per_bin, chunks=chunks)
