"""Signal levels.

dBFS follows the AES17 convention: a full-scale sine wave (peak 1.0, RMS
1/√2) reads 0 dBFS, so a full-scale square wave reads about +3.01 dBFS.
"""

from __future__ import annotations

import math

import numpy as np
from numpy.typing import ArrayLike

FULL_SCALE_SINE_RMS = 1 / math.sqrt(2)
"""RMS of a sine wave with peak amplitude 1.0: the 0 dBFS reference."""


def rms(samples: ArrayLike) -> float:
    """Root mean square of the samples.

    Raises:
        ValueError: If there are no samples.
    """
    signal = np.asarray(samples, dtype=np.float64)
    if signal.size == 0:
        msg = "cannot compute the RMS of an empty signal"
        raise ValueError(msg)
    return float(np.sqrt(np.mean(signal**2)))


def rms_dbfs(samples: ArrayLike) -> float:
    """RMS level in dBFS (AES17); ``-inf`` for digital silence."""
    value = rms(samples)
    if value == 0:
        return -math.inf
    return 20 * math.log10(value / FULL_SCALE_SINE_RMS)
