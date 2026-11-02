import math

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from aviscape_dsp import NDSI_ANTHROPHONY_HZ, NDSI_BIOPHONY_HZ, ndsi, spectrogram

SR = 22_050
BIN_HZ = SR / 512
T = np.arange(SR * 2) / SR


def tone(bin_index: int, amplitude: float = 0.3) -> np.ndarray:
    """A sine centred on an FFT bin, so its energy stays within that bin and its neighbours."""
    return amplitude * np.sin(2 * np.pi * bin_index * BIN_HZ * T)


def bins_in(band: tuple[float, float], frequencies: np.ndarray) -> int:
    return int(np.count_nonzero((frequencies >= band[0]) & (frequencies < band[1])))


def test_equal_power_in_both_bands_gives_zero() -> None:
    signal = tone(35) + tone(117)  # 1507 Hz (anthrophony) and 5039 Hz (biophony)
    assert ndsi(spectrogram(signal, SR)) == pytest.approx(0.0, abs=1e-9)


def test_biophony_only_gives_plus_one() -> None:
    assert ndsi(spectrogram(tone(117), SR)) == pytest.approx(1.0, abs=1e-9)


def test_anthrophony_only_gives_minus_one() -> None:
    assert ndsi(spectrogram(tone(35), SR)) == pytest.approx(-1.0, abs=1e-9)


def test_white_noise_matches_the_ratio_of_band_widths() -> None:
    # White noise has the same expected power in every bin, so NDSI is set by
    # how many bins each band covers: 23 for anthrophony, 209 for biophony.
    noise = np.random.default_rng(42).normal(0.0, 0.1, SR * 60)
    spec = spectrogram(noise, SR)
    a = bins_in(NDSI_ANTHROPHONY_HZ, spec.frequencies_hz)
    b = bins_in(NDSI_BIOPHONY_HZ, spec.frequencies_hz)
    assert (a, b) == (23, 209)
    assert ndsi(spec) == pytest.approx((b - a) / (b + a), abs=0.01)


def test_silence_is_undefined() -> None:
    assert math.isnan(ndsi(spectrogram(np.zeros(SR), SR)))


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"biophony_hz": (12_000.0, 13_000.0)}, "above Nyquist"),
        ({"anthrophony_hz": (2_000.0, 1_000.0)}, "low < high"),
    ],
)
def test_invalid_bands_are_rejected(kwargs: dict[str, tuple[float, float]], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        ndsi(spectrogram(np.zeros(1024), SR), **kwargs)


signals = st.builds(
    lambda seed, freq, amp, noise: (
        amp * np.sin(2 * np.pi * freq * T[:4096])
        + np.random.default_rng(seed).normal(0.0, noise, 4096)
    ),
    seed=st.integers(min_value=0, max_value=2**32 - 1),
    freq=st.floats(min_value=500.0, max_value=10_500.0),
    amp=st.floats(min_value=0.0, max_value=1.0),
    noise=st.floats(min_value=1e-4, max_value=0.5),
)


@given(signal=signals)
def test_ndsi_is_bounded(signal: np.ndarray) -> None:
    assert -1.0 <= ndsi(spectrogram(signal, SR)) <= 1.0


@given(signal=signals, gain=st.floats(min_value=1e-3, max_value=1e3))
def test_ndsi_does_not_depend_on_gain(signal: np.ndarray, gain: float) -> None:
    original = ndsi(spectrogram(signal, SR))
    scaled = ndsi(spectrogram(gain * signal, SR))
    assert scaled == pytest.approx(original, rel=1e-9, abs=1e-12)
