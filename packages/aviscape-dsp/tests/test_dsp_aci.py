import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from aviscape_dsp import acoustic_complexity, spectrogram

SR = 22_050
BIN_HZ = SR / 512
T = np.arange(SR * 10) / SR


def tone(bin_index: int = 117, amplitude: float = 0.3) -> np.ndarray:
    return amplitude * np.sin(2 * np.pi * bin_index * BIN_HZ * T)


def tone_bin_aci(signal: np.ndarray, bin_index: int = 117) -> float:
    return float(acoustic_complexity(spectrogram(signal, SR)).per_bin[bin_index])


def test_a_stationary_tone_scores_near_zero_in_its_bin() -> None:
    assert tone_bin_aci(tone()) < 1e-6


def test_modulated_tones_rank_above_steady_ones() -> None:
    slow = tone() * (1 + 0.5 * np.sin(2 * np.pi * 0.5 * T))
    fast = tone() * (1 + 0.5 * np.sin(2 * np.pi * 8.0 * T))
    gated = tone() * ((T * 8) % 1 < 0.5)
    values = [tone_bin_aci(s) for s in (tone(), slow, fast, gated)]
    assert values == sorted(values)
    assert values[0] < 1e-6 < values[1]


def test_loudness_does_not_matter() -> None:
    signal = tone() * (1 + 0.5 * np.sin(2 * np.pi * 4.0 * T))
    assert tone_bin_aci(10 * signal) == pytest.approx(tone_bin_aci(signal), rel=1e-9)


def test_silent_bins_score_zero_and_the_total_sums_the_bins() -> None:
    result = acoustic_complexity(spectrogram(np.zeros(SR), SR))
    assert result.total == 0.0
    assert np.all(result.per_bin == 0.0)
    noise = np.random.default_rng(0).normal(0, 0.1, SR)
    result = acoustic_complexity(spectrogram(noise, SR))
    assert result.total == pytest.approx(float(result.per_bin.sum()))


def test_chunks_split_the_window_and_add_up() -> None:
    noise = np.random.default_rng(1).normal(0, 0.1, T.size)
    spec = spectrogram(noise, SR)
    whole = acoustic_complexity(spec)
    chunked = acoustic_complexity(spec, chunk_s=2.0)
    assert whole.chunks == 1
    assert chunked.chunks == 5
    # For stationary noise, the change-to-intensity ratio of each chunk is about that of the
    # whole window, so adding up five chunks gives about five times the total.
    assert chunked.total == pytest.approx(5 * whole.total, rel=0.05)


@pytest.mark.parametrize("chunk_s", [0.01, 60.0])
def test_rejects_chunks_without_two_frames_or_longer_than_the_window(chunk_s: float) -> None:
    with pytest.raises(ValueError, match="chunk must hold"):
        acoustic_complexity(spectrogram(np.zeros(SR), SR), chunk_s=chunk_s)


@settings(max_examples=25, deadline=None)
@given(st.integers(0, 2**32 - 1))
def test_values_are_non_negative_and_deterministic(seed: int) -> None:
    spec = spectrogram(np.random.default_rng(seed).normal(0, 0.1, SR), SR)
    a, b = acoustic_complexity(spec), acoustic_complexity(spec)
    assert np.all(a.per_bin >= 0)
    np.testing.assert_array_equal(a.per_bin, b.per_bin)
