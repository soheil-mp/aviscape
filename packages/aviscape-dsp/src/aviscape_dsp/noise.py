"""Background noise (BGN) and signal-to-noise ratio (SNR).

Background noise is estimated with the mode of the decibel histogram, the approach Towsey
(2017) uses for long-duration recordings, after the adaptive level equalisation of Lamel et
al. (1981). Within a window, most frames in a frequency bin hold only background noise, so
the most common decibel value is the noise level, and short loud events (calls, passing
cars) do not move it, unlike the mean.

For one array of decibel values:

1. Build a histogram with ``histogram_bins`` equal-width bins between the smallest and the
   largest value.
2. Smooth the counts with a centred moving average of ``smoothing`` bins.
3. The noise level is the centre of the highest bin, plus ``n_sd`` times the standard
   deviation of the values below it (around the mode).

With ``n_sd = 0`` (the default here), the estimate for stationary Gaussian noise is unbiased:
each periodogram bin is exponentially distributed, and the logarithm of an exponential
variable peaks exactly at its mean. A positive ``n_sd`` sets the level a little above the
noise floor, which is useful when the level is subtracted for noise reduction.

The mode of that distribution is broad, so a single bin's estimate scatters: for one minute
of stationary noise (2,583 frames of 512 samples) the standard deviation is about 0.7 dB,
while the median over all bins stays within about 0.1 dB of the true level. The mode stays
put while calls occupy a minority of frames (up to about 10 % for a steady tone); events
that fill more of the window become the background, as they should.

Spectral levels are in dB relative to 1 FS² of power per frequency bin, that is
``10 * log10(psd * bin_width_hz)``. Envelope levels are in dB relative to full scale.

References:
    Towsey, M. (2017). *The calculation of acoustic indices derived from long-duration
    recordings of the natural environment.* QUT ePrints 110634, Queensland University of
    Technology.

    Lamel, L., Rabiner, L., Rosenberg, A. & Wilpon, J. (1981). An improved endpoint detector
    for isolated word recognition. *IEEE Transactions on Acoustics, Speech, and Signal
    Processing*, 29(4), 777-785.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from numpy.typing import ArrayLike, NDArray

from aviscape_dsp.spectrum import DEFAULT_FRAME_LENGTH, Spectrogram

HISTOGRAM_BINS = 100
"""Default number of histogram bins for the mode estimate."""

SMOOTHING_BINS = 5
"""Default width of the moving average applied to the histogram counts."""

FLOOR_DB = -200.0
"""Level that stands in for zero power, so digital silence has a finite noise level."""


@dataclass(frozen=True, slots=True)
class SignalToNoise:
    """Signal-to-noise ratio of a window from its frame envelope.

    Attributes:
        snr_db: Loudest frame minus the background noise of the envelope, in dB.
        background_db: Background noise of the envelope, dB re full scale.
        peak_db: Loudest frame of the envelope, dB re full scale.
    """

    snr_db: float
    background_db: float
    peak_db: float


def mode_noise_level(
    values_db: ArrayLike,
    *,
    histogram_bins: int = HISTOGRAM_BINS,
    smoothing: int = SMOOTHING_BINS,
    n_sd: float = 0.0,
) -> float:
    """Noise level of a set of decibel values from the mode of their histogram.

    Raises:
        ValueError: If there are no values or the parameters are invalid.
    """
    values = np.asarray(values_db, dtype=np.float64).ravel()
    if values.size == 0:
        msg = "need at least one value"
        raise ValueError(msg)
    if histogram_bins < 1 or smoothing < 1 or n_sd < 0:
        msg = "histogram_bins and smoothing must be >= 1 and n_sd >= 0"
        raise ValueError(msg)
    low, high = float(values.min()), float(values.max())
    if low == high:
        return low
    counts, edges = np.histogram(values, bins=histogram_bins, range=(low, high))
    kernel = np.ones(smoothing) / smoothing
    smoothed = np.convolve(counts.astype(np.float64), kernel, mode="same")
    peak = int(np.argmax(smoothed))
    mode = float((edges[peak] + edges[peak + 1]) / 2)
    if n_sd == 0:
        return mode
    below = values[values < mode]
    sd = float(np.sqrt(np.mean((below - mode) ** 2))) if below.size else 0.0
    return mode + n_sd * sd


def spectral_levels_db(spec: Spectrogram) -> NDArray[np.float64]:
    """Power per frequency bin of every frame in dB re 1 FS², shape ``(n_frames, n_bins)``."""
    power = spec.psd * spec.bin_width_hz
    with np.errstate(divide="ignore"):
        levels = 10 * np.log10(power)
    return np.asarray(np.maximum(levels, FLOOR_DB), dtype=np.float64)


def background_noise(
    spec: Spectrogram,
    *,
    histogram_bins: int = HISTOGRAM_BINS,
    smoothing: int = SMOOTHING_BINS,
    n_sd: float = 0.0,
) -> NDArray[np.float64]:
    """Background noise of every frequency bin, dB re 1 FS² per bin, shape ``(n_bins,)``."""
    levels = spectral_levels_db(spec)
    return np.asarray(
        [
            mode_noise_level(
                levels[:, k], histogram_bins=histogram_bins, smoothing=smoothing, n_sd=n_sd
            )
            for k in range(levels.shape[1])
        ],
        dtype=np.float64,
    )


def envelope_db(
    samples: ArrayLike, *, frame_length: int = DEFAULT_FRAME_LENGTH
) -> NDArray[np.float64]:
    """Largest absolute sample of each non-overlapping frame, in dB re full scale.

    Trailing samples that do not fill a frame are dropped.

    Raises:
        ValueError: If the signal is shorter than one frame.
    """
    signal = np.asarray(samples, dtype=np.float64)
    if signal.ndim != 1 or signal.size < frame_length:
        msg = f"need a 1-D signal of at least {frame_length} samples, got shape {signal.shape}"
        raise ValueError(msg)
    frames = sliding_window_view(signal, frame_length)[::frame_length]
    peaks = np.abs(frames).max(axis=1)
    with np.errstate(divide="ignore"):
        levels = 20 * np.log10(peaks)
    return np.asarray(np.maximum(levels, FLOOR_DB), dtype=np.float64)


def signal_to_noise(
    samples: ArrayLike,
    *,
    frame_length: int = DEFAULT_FRAME_LENGTH,
    histogram_bins: int = HISTOGRAM_BINS,
    smoothing: int = SMOOTHING_BINS,
) -> SignalToNoise:
    """SNR of a window: its loudest frame relative to the background noise of its envelope."""
    envelope = envelope_db(samples, frame_length=frame_length)
    background = mode_noise_level(envelope, histogram_bins=histogram_bins, smoothing=smoothing)
    peak = float(envelope.max())
    return SignalToNoise(snr_db=peak - background, background_db=background, peak_db=peak)
