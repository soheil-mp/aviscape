"""Audio frame model: turn whatever a source delivers into the analysis format.

Every index in this package expects the same input, an :class:`AudioFrame`:

- **mono**: multi-channel audio is down-mixed by averaging the channels;
- **float64 in [-1, 1]**: integer PCM is scaled by its full-scale value (``2**(bits-1)``), so
  the most negative code maps to exactly -1.0; unsigned 8-bit PCM is centred on 128 first;
- **22.05 kHz**: other rates are resampled with a polyphase FIR filter
  (:func:`scipy.signal.resample_poly`), which keeps the level of in-band tones and removes
  content above the new Nyquist frequency;
- **no DC offset**: the mean is subtracted, so a biased microphone does not leak energy into
  the lowest frequency bin.

The steps run in that order. Nothing here is adaptive or learned: the same samples always give
the same frame.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.signal import resample_poly

ANALYSIS_SAMPLE_RATE = 22_050
"""Sample rate of every analysis frame, in Hz. Its Nyquist frequency (11.025 kHz) covers the
biophony band of Kasten et al. (2012)."""


@dataclass(frozen=True, slots=True)
class AudioFrame:
    """Mono float64 audio at a known sample rate.

    Attributes:
        samples: One-dimensional float64 samples, nominally within [-1, 1].
        sample_rate: Samples per second.
        dc_offset: Mean that was removed from the samples (0.0 when DC removal was off).
    """

    samples: NDArray[np.float64]
    sample_rate: int
    dc_offset: float = 0.0

    @property
    def duration_s(self) -> float:
        """Length of the frame in seconds."""
        return self.samples.size / self.sample_rate


def to_float(samples: ArrayLike) -> NDArray[np.float64]:
    """Convert PCM samples of any common type to float64 full-scale units.

    Signed integers are divided by ``2**(bits-1)``; ``uint8`` is centred on 128 and divided by
    128; floating-point samples are passed through unchanged (they are assumed to be in
    full-scale units already).

    Raises:
        TypeError: For unsupported types such as complex numbers, booleans or wide unsigned
            integers.
    """
    array = np.asarray(samples)
    kind = array.dtype.kind
    if kind == "f":
        return array.astype(np.float64)
    if kind == "i":
        full_scale = float(2 ** (8 * array.dtype.itemsize - 1))
        return array.astype(np.float64) / full_scale
    if kind == "u" and array.dtype.itemsize == 1:
        return (array.astype(np.float64) - 128.0) / 128.0
    msg = f"unsupported sample type {array.dtype}"
    raise TypeError(msg)


def downmix(samples: NDArray[np.float64], *, channel_axis: int = -1) -> NDArray[np.float64]:
    """Average the channels of a two-dimensional signal; one-dimensional input passes through.

    Args:
        samples: Signal of shape ``(n,)`` or ``(n, channels)`` (or ``(channels, n)`` with
            ``channel_axis=0``).
        channel_axis: Axis that holds the channels.

    Raises:
        ValueError: For more than two dimensions.
    """
    if samples.ndim == 1:
        return samples
    if samples.ndim != 2:  # noqa: PLR2004 - samples by channels
        msg = f"expected a 1-D or 2-D signal, got shape {samples.shape}"
        raise ValueError(msg)
    return np.asarray(samples.mean(axis=channel_axis), dtype=np.float64)


def resample(
    samples: NDArray[np.float64], from_rate: int, to_rate: int = ANALYSIS_SAMPLE_RATE
) -> NDArray[np.float64]:
    """Resample a mono signal with a polyphase FIR filter.

    The up/down factors are ``to_rate`` and ``from_rate`` divided by their greatest common
    divisor, for example 147/160 for 48 kHz to 22.05 kHz.

    Raises:
        ValueError: If a rate is not positive.
    """
    if from_rate <= 0 or to_rate <= 0:
        msg = f"sample rates must be positive, got {from_rate} and {to_rate}"
        raise ValueError(msg)
    if from_rate == to_rate:
        return samples
    common = math.gcd(from_rate, to_rate)
    return np.asarray(
        resample_poly(samples, to_rate // common, from_rate // common), dtype=np.float64
    )


def prepare(
    samples: ArrayLike,
    sample_rate: int,
    *,
    channel_axis: int = -1,
    target_rate: int = ANALYSIS_SAMPLE_RATE,
    remove_dc: bool = True,
) -> AudioFrame:
    """Convert raw PCM into an analysis :class:`AudioFrame`.

    Args:
        samples: PCM of shape ``(n,)`` or ``(n, channels)``, integer or float.
        sample_rate: Sample rate of ``samples`` in Hz.
        channel_axis: Axis of ``samples`` that holds the channels.
        target_rate: Sample rate of the result.
        remove_dc: Subtract the mean after resampling.

    Raises:
        ValueError: If the signal is empty or the rates are invalid.
    """
    mono = downmix(to_float(samples), channel_axis=channel_axis)
    if mono.size == 0:
        msg = "cannot prepare an empty signal"
        raise ValueError(msg)
    signal = resample(mono, sample_rate, target_rate)
    offset = float(signal.mean()) if remove_dc else 0.0
    if remove_dc:
        signal = signal - offset
    return AudioFrame(samples=signal, sample_rate=target_rate, dc_offset=offset)
