"""Acoustic indices.

Each index documents its definition, defaults and source. More indices arrive
with roadmap milestone M2.
"""

from __future__ import annotations

import math

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
