"""Short-time power spectral density.

Conventions (used by every index in this package):

- Frames are windowed with a periodic Hann window. The default frame length
  of 512 samples without overlap follows Towsey (2017); at 22.05 kHz it gives
  257 bins of about 43 Hz.
- Values are a one-sided power spectral density in units of full-scale
  squared per hertz (FS²/Hz). The DC and Nyquist bins are not doubled.
- The scaling preserves power (Parseval): for a stationary signal,
  ``sum(mean_psd) * bin_width_hz`` equals the mean square of the samples.
- Arithmetic is float64; storage formats may downcast later.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from numpy.typing import ArrayLike, NDArray
from scipy.signal import get_window

DEFAULT_FRAME_LENGTH = 512


@dataclass(frozen=True, slots=True)
class Spectrogram:
    """A one-sided power spectral density per frame.

    Attributes:
        psd: Array of shape ``(n_frames, n_bins)`` in FS²/Hz.
        frequencies_hz: Centre frequency of each bin, shape ``(n_bins,)``.
        sample_rate: Sample rate of the analysed signal in Hz.
        frame_length: Samples per frame (also the FFT size).
        hop_length: Samples between the starts of consecutive frames.
    """

    psd: NDArray[np.float64]
    frequencies_hz: NDArray[np.float64]
    sample_rate: int
    frame_length: int
    hop_length: int

    @property
    def bin_width_hz(self) -> float:
        """Spacing between frequency bins in Hz."""
        return self.sample_rate / self.frame_length

    @property
    def n_frames(self) -> int:
        """Number of frames."""
        return int(self.psd.shape[0])

    def mean_psd(self) -> NDArray[np.float64]:
        """Average the PSD over frames (a Welch-style estimate)."""
        return np.asarray(self.psd.mean(axis=0), dtype=np.float64)

    def band_power(self, low_hz: float, high_hz: float) -> float:
        """Power in the band ``[low_hz, high_hz)``, in FS² (mean over frames)."""
        if not 0 <= low_hz < high_hz:
            msg = f"band must satisfy 0 <= low < high, got [{low_hz}, {high_hz})"
            raise ValueError(msg)
        in_band = (self.frequencies_hz >= low_hz) & (self.frequencies_hz < high_hz)
        return float(self.mean_psd()[in_band].sum() * self.bin_width_hz)


def spectrogram(
    samples: ArrayLike,
    sample_rate: int,
    *,
    frame_length: int = DEFAULT_FRAME_LENGTH,
    hop_length: int | None = None,
) -> Spectrogram:
    """Compute the short-time power spectral density of a mono signal.

    Args:
        samples: Mono samples, nominally within [-1, 1].
        sample_rate: Samples per second.
        frame_length: Samples per frame and FFT size.
        hop_length: Samples between frame starts; defaults to ``frame_length``
            (no overlap). Trailing samples that do not fill a frame are dropped.

    Returns:
        The spectrogram with density scaling as described in the module docs.

    Raises:
        ValueError: If the input is not 1-D, too short for one frame, or the
            parameters are not positive.
    """
    signal = np.asarray(samples, dtype=np.float64)
    hop = frame_length if hop_length is None else hop_length
    if signal.ndim != 1:
        msg = f"samples must be one-dimensional, got shape {signal.shape}"
        raise ValueError(msg)
    if sample_rate <= 0 or frame_length <= 1 or hop <= 0:
        msg = "sample_rate, frame_length (> 1) and hop_length must be positive"
        raise ValueError(msg)
    if signal.size < frame_length:
        msg = f"need at least {frame_length} samples for one frame, got {signal.size}"
        raise ValueError(msg)

    window = np.asarray(get_window("hann", frame_length, fftbins=True), dtype=np.float64)
    frames = sliding_window_view(signal, frame_length)[::hop]
    spectrum = np.fft.rfft(frames * window, axis=1)
    psd = (np.abs(spectrum) ** 2) / (sample_rate * float(np.sum(window**2)))
    # One-sided: double every bin except DC and, for even lengths, Nyquist.
    last = -1 if frame_length % 2 == 0 else None
    psd[:, 1:last] *= 2.0
    frequencies = np.fft.rfftfreq(frame_length, d=1.0 / sample_rate)
    return Spectrogram(
        psd=psd,
        frequencies_hz=frequencies,
        sample_rate=sample_rate,
        frame_length=frame_length,
        hop_length=hop,
    )
