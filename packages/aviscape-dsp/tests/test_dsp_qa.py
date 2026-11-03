import math

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from aviscape_dsp.qa import (
    Run,
    assess,
    clipping_ratio,
    constant_runs,
    crest_factor_db,
    dc_offset,
    dropouts,
    peak_dbfs,
    silence_runs,
)

SR = 22_050


def sine(amplitude: float = 0.5, seconds: float = 1.0, freq_hz: float = 1_000.0) -> np.ndarray:
    t = np.arange(round(SR * seconds)) / SR
    return amplitude * np.sin(2 * np.pi * freq_hz * t)


def noise(seconds: float = 1.0, seed: int = 0) -> np.ndarray:
    return np.random.default_rng(seed).normal(0.0, 0.05, round(SR * seconds))


class TestClean:
    def test_clean_noise_raises_no_flags(self) -> None:
        quality = assess(noise(), SR)
        assert quality.clipping_ratio == 0.0
        assert abs(quality.dc_offset) < 1e-3
        assert quality.silence_runs == quality.dropout_runs == 0
        assert quality.silence_ratio == 0.0
        assert quality.rms_dbfs == pytest.approx(20 * math.log10(0.05 * math.sqrt(2)), abs=0.1)


class TestFaults:
    def test_clipping_is_caught(self) -> None:
        clipped = np.clip(sine(amplitude=2.0), -1.0, 1.0)
        assert clipping_ratio(clipped) > 0.5
        assert clipping_ratio(sine(amplitude=0.9)) == 0.0

    def test_dc_offset_is_caught(self) -> None:
        assert dc_offset(noise() + 0.2) == pytest.approx(0.2, abs=1e-3)

    def test_peak_level(self) -> None:
        assert peak_dbfs(sine(amplitude=0.5)) == pytest.approx(-6.02, abs=0.01)
        assert peak_dbfs(np.zeros(10)) == -math.inf

    @pytest.mark.parametrize(
        ("signal", "expected_db"),
        [
            (sine(), 3.01),
            (np.sign(sine()) * 0.5, 0.0),
        ],
    )
    def test_crest_factor_of_known_waveforms(self, signal: np.ndarray, expected_db: float) -> None:
        assert crest_factor_db(signal) == pytest.approx(expected_db, abs=0.02)

    def test_crest_factor_flags_heavy_limiting_and_spikes(self) -> None:
        limited = np.clip(sine(amplitude=10.0), -0.5, 0.5)
        spike = np.zeros(SR)
        spike[100] = 1.0
        assert crest_factor_db(limited) < 0.5
        assert crest_factor_db(spike) > 40
        assert math.isnan(crest_factor_db(np.zeros(10)))

    def test_digital_silence_is_caught(self) -> None:
        signal = noise(2.0)
        signal[SR // 2 : SR] = 0.0  # 0.5 s muted
        runs = silence_runs(signal, SR)
        assert runs == [Run(SR // 2, SR // 2)]
        quality = assess(signal, SR)
        assert quality.silence_ratio == pytest.approx(0.25)
        assert quality.dropout_runs == 0

    def test_short_zero_gaps_are_dropouts_not_silence(self) -> None:
        signal = noise()
        signal[1_000:1_200] = 0.0  # about 9 ms
        assert silence_runs(signal, SR) == []
        assert dropouts(signal, SR) == [Run(1_000, 200)]

    def test_held_values_are_dropouts(self) -> None:
        signal = noise()
        signal[5_000:5_441] = signal[4_999]  # a 20 ms hold of the last good sample
        runs = dropouts(signal, SR)
        assert runs == [Run(4_999, 442)]

    def test_runs_shorter_than_the_minimum_are_ignored(self) -> None:
        signal = noise()
        signal[100:110] = 0.25  # under 0.5 ms
        assert dropouts(signal, SR) == []


class TestConstantRuns:
    def test_finds_every_run_with_its_start_and_length(self) -> None:
        signal = np.array([1, 1, 2, 3, 3, 3, 0, 0], dtype=float)
        assert constant_runs(signal, 2) == [Run(0, 2), Run(3, 3), Run(6, 2)]
        assert constant_runs(signal, 1)[1] == Run(2, 1)

    def test_rejects_a_zero_minimum(self) -> None:
        with pytest.raises(ValueError, match="at least 1"):
            constant_runs(np.zeros(3), 0)

    @given(st.lists(st.integers(-3, 3), min_size=1, max_size=200))
    def test_runs_of_length_one_partition_the_signal(self, values: list[int]) -> None:
        runs = constant_runs(np.asarray(values, dtype=float), 1)
        assert sum(r.length for r in runs) == len(values)
        assert [r.start for r in runs] == sorted(r.start for r in runs)


@pytest.mark.parametrize("bad", [np.zeros(0), np.zeros((2, 2))])
def test_rejects_empty_and_multichannel_input(bad: np.ndarray) -> None:
    with pytest.raises(ValueError, match="one-dimensional"):
        assess(bad, SR)
