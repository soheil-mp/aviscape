import math

import numpy as np
import pytest

from aviscape_dsp import spectrogram
from aviscape_dsp.noise import (
    FLOOR_DB,
    background_noise,
    envelope_db,
    mode_noise_level,
    signal_to_noise,
    spectral_levels_db,
)

SR = 22_050
SIGMA = 0.05


def white_noise(seconds: float = 60.0, seed: int = 3) -> np.ndarray:
    return np.random.default_rng(seed).normal(0.0, SIGMA, round(SR * seconds))


# Each interior bin of white noise holds 2 sigma^2 / N of power (N = 512, see spectrum.py).
EXPECTED_BIN_DB = 10 * math.log10(2 * SIGMA**2 / 512)


def test_background_of_stationary_noise_is_its_true_level() -> None:
    error = background_noise(spectrogram(white_noise(), SR))[1:-1] - EXPECTED_BIN_DB
    # Across bins the estimate is unbiased; a single bin scatters by about 0.7 dB (1 SD).
    assert abs(float(np.median(error))) < 0.15
    assert abs(float(np.mean(error))) < 0.25
    assert float(np.std(error)) < 0.8
    assert float(np.abs(error).max()) < 3.0


def test_intermittent_loud_events_do_not_move_the_background() -> None:
    signal = white_noise()
    t = np.arange(signal.size) / SR
    # A call of varying loudness about 8 % of the time, near 5 kHz.
    gate = np.sin(2 * np.pi * 0.2 * t) > 0.97
    loudness = 0.05 + 0.25 * (0.5 + 0.5 * np.sin(2 * np.pi * 0.013 * t))
    calls = gate * loudness * np.sin(2 * np.pi * 4_996.0 * t)
    spec = spectrogram(signal + calls, SR)
    band = np.abs(spec.frequencies_hz - 4_996.0) < 50.0  # the bin of the call and its neighbours
    mean_level = 10 * np.log10(spec.mean_psd()[band] * spec.bin_width_hz)
    assert np.all(mean_level > EXPECTED_BIN_DB + 10)  # the mean is dominated by the calls ...
    background = background_noise(spec)[band]
    assert np.abs(background - EXPECTED_BIN_DB).max() < 2.5  # ... the mode is not


def test_n_sd_raises_the_level_above_the_mode() -> None:
    spec = spectrogram(white_noise(10.0), SR)
    plain = background_noise(spec)
    raised = background_noise(spec, n_sd=0.5)
    assert np.all(raised > plain)


def test_mode_noise_level_of_simple_inputs() -> None:
    assert mode_noise_level([-40.0] * 5) == -40.0
    values = [-60.0] * 50 + [-30.0, -20.0, -10.0]
    assert mode_noise_level(values, histogram_bins=50, smoothing=1) == pytest.approx(-59.5)


@pytest.mark.parametrize("kwargs", [{"histogram_bins": 0}, {"smoothing": 0}, {"n_sd": -1.0}])
def test_mode_noise_level_rejects_bad_parameters(kwargs: dict[str, float]) -> None:
    with pytest.raises(ValueError, match=">= 1"):
        mode_noise_level([1.0, 2.0], **kwargs)  # type: ignore[arg-type]


def test_mode_noise_level_rejects_empty_input() -> None:
    with pytest.raises(ValueError, match="at least one"):
        mode_noise_level([])


def test_silence_has_a_finite_floor() -> None:
    spec = spectrogram(np.zeros(SR), SR)
    assert np.all(spectral_levels_db(spec) == FLOOR_DB)
    assert np.all(background_noise(spec) == FLOOR_DB)
    assert np.all(envelope_db(np.zeros(SR)) == FLOOR_DB)


def test_envelope_takes_the_peak_of_each_frame() -> None:
    signal = np.zeros(1_100)
    signal[10], signal[600] = 0.5, -0.25
    np.testing.assert_allclose(envelope_db(signal), [-6.0206, -12.0412], atol=1e-4)
    with pytest.raises(ValueError, match="at least 512"):
        envelope_db(np.zeros(100))


def test_snr_of_a_loud_burst_over_noise() -> None:
    signal = white_noise(10.0)
    t = np.arange(SR // 2) / SR
    signal[SR * 5 : SR * 5 + SR // 2] += 0.5 * np.sin(2 * np.pi * 3_000 * t)
    snr = signal_to_noise(signal)
    assert 20 * math.log10(0.5) < snr.peak_db < 0.0
    # Frame peaks of Gaussian noise sit about 3 sigma above zero.
    assert snr.background_db == pytest.approx(20 * math.log10(3 * SIGMA), abs=1.5)
    assert snr.snr_db == pytest.approx(snr.peak_db - snr.background_db)
    assert snr.snr_db > signal_to_noise(white_noise(10.0)).snr_db + 6
