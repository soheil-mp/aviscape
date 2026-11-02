import numpy as np
import pytest

from aviscape_dsp import Spectrogram, spectrogram

SR = 22_050


def white_noise(sigma: float, seconds: float, seed: int = 0) -> np.ndarray:
    return np.random.default_rng(seed).normal(0.0, sigma, int(SR * seconds))


def total_power(spec: Spectrogram) -> float:
    return float(spec.mean_psd().sum() * spec.bin_width_hz)


def test_shape_and_frequency_axis() -> None:
    spec = spectrogram(np.zeros(2048), SR)
    assert spec.psd.shape == (4, 257)
    assert spec.n_frames == 4
    assert spec.frequencies_hz[0] == 0
    assert spec.frequencies_hz[-1] == SR / 2
    assert spec.bin_width_hz == pytest.approx(43.06640625)


def test_hop_length_controls_overlap_and_trailing_samples_are_dropped() -> None:
    assert spectrogram(np.zeros(2048), SR, hop_length=256).n_frames == 7
    assert spectrogram(np.zeros(1100), SR).n_frames == 2


@pytest.mark.parametrize("frame_length", [512, 511])
def test_parseval_white_noise_power_is_preserved(frame_length: int) -> None:
    spec = spectrogram(white_noise(0.1, 10), SR, frame_length=frame_length)
    assert total_power(spec) == pytest.approx(0.01, rel=0.02)


def test_parseval_sine_power_is_amplitude_squared_over_two() -> None:
    t = np.arange(SR * 10) / SR
    spec = spectrogram(0.5 * np.sin(2 * np.pi * 3000.3 * t), SR)
    assert total_power(spec) == pytest.approx(0.125, rel=0.01)


def test_tone_energy_sits_at_its_frequency() -> None:
    t = np.arange(SR * 2) / SR
    spec = spectrogram(0.3 * np.sin(2 * np.pi * 4000.0 * t), SR)
    peak = spec.frequencies_hz[np.argmax(spec.mean_psd())]
    assert abs(peak - 4000.0) <= spec.bin_width_hz / 2


def test_band_power_splits_total_power() -> None:
    spec = spectrogram(white_noise(0.1, 5), SR)
    low, high = spec.band_power(0, 5000), spec.band_power(5000, SR)
    assert low + high == pytest.approx(total_power(spec), rel=1e-12)


@pytest.mark.parametrize(
    ("samples", "kwargs", "message"),
    [
        (np.zeros((2, 512)), {}, "one-dimensional"),
        (np.zeros(100), {}, "at least 512"),
        (np.zeros(1024), {"frame_length": 1}, "positive"),
        (np.zeros(1024), {"hop_length": 0}, "positive"),
    ],
)
def test_invalid_input_is_rejected(
    samples: np.ndarray, kwargs: dict[str, int], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        spectrogram(samples, SR, **kwargs)


def test_invalid_band_is_rejected() -> None:
    spec = spectrogram(np.zeros(1024), SR)
    with pytest.raises(ValueError, match="band"):
        spec.band_power(2000, 1000)
