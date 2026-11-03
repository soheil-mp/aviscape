import math

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from aviscape_dsp import acoustic_entropy, spectral_entropy, spectrogram, temporal_entropy

SR = 22_050
T = np.arange(SR * 10) / SR


def white_noise(seed: int = 0) -> np.ndarray:
    return np.random.default_rng(seed).normal(0.0, 0.1, T.size)


def test_white_noise_has_near_maximal_entropy() -> None:
    noise = white_noise()
    assert temporal_entropy(noise) > 0.95
    assert spectral_entropy(spectrogram(noise, SR)) > 0.97
    assert acoustic_entropy(noise, spectrogram(noise, SR)) > 0.92


def test_a_pure_tone_has_low_spectral_and_high_temporal_entropy() -> None:
    tone = 0.3 * np.sin(2 * np.pi * 117 * (SR / 512) * T)  # centred on bin 117
    assert spectral_entropy(spectrogram(tone, SR)) < 0.3
    assert temporal_entropy(tone) > 0.99


def test_brief_bursts_lower_temporal_entropy() -> None:
    # Ht is logarithmic: energy confined to a fraction f of n samples gives about
    # log(f * n) / log(n), so 1 % of ten seconds still scores about 0.65.
    noise = white_noise()
    one_percent = temporal_entropy(noise * ((T % 2) < 0.02))
    ten_percent = temporal_entropy(noise * ((T % 2) < 0.2))
    assert one_percent < ten_percent < temporal_entropy(noise) - 0.15
    assert one_percent == pytest.approx(np.log(0.01 * T.size) / np.log(T.size), abs=0.1)


def test_more_tones_raise_spectral_entropy() -> None:
    def tones(n: int) -> float:
        signal = sum(np.sin(2 * np.pi * (20 + 20 * k) * (SR / 512) * T) for k in range(n))
        return spectral_entropy(spectrogram(np.asarray(signal), SR))

    assert tones(1) < tones(3) < tones(9)


def test_silence_is_undefined() -> None:
    silence = np.zeros(SR)
    assert math.isnan(temporal_entropy(silence))
    assert math.isnan(spectral_entropy(spectrogram(silence, SR)))
    assert math.isnan(acoustic_entropy(silence, spectrogram(silence, SR)))


def test_temporal_entropy_rejects_multichannel_input() -> None:
    with pytest.raises(ValueError, match="one-dimensional"):
        temporal_entropy(np.zeros((10, 2)))


@settings(max_examples=25, deadline=None)
@given(seed=st.integers(0, 2**32 - 1), gain=st.floats(1e-3, 10.0))
def test_entropies_are_bounded_and_independent_of_gain(seed: int, gain: float) -> None:
    signal = np.random.default_rng(seed).normal(0.0, 0.1, SR) * np.linspace(0, 1, SR)
    ht, hf = temporal_entropy(signal), spectral_entropy(spectrogram(signal, SR))
    assert 0.0 <= ht <= 1.0
    assert 0.0 <= hf <= 1.0
    assert temporal_entropy(gain * signal) == pytest.approx(ht, rel=1e-9)
    assert spectral_entropy(spectrogram(gain * signal, SR)) == pytest.approx(hf, rel=1e-9)
