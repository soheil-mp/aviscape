import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from aviscape_dsp import ANALYSIS_SAMPLE_RATE, prepare, rms_dbfs, spectrogram
from aviscape_dsp.audio import downmix, resample, to_float


def sine(
    freq_hz: float, sample_rate: int, seconds: float = 2.0, amplitude: float = 0.5
) -> np.ndarray:
    t = np.arange(round(sample_rate * seconds)) / sample_rate
    return amplitude * np.sin(2 * np.pi * freq_hz * t)


def peak_frequency(samples: np.ndarray, sample_rate: int) -> float:
    spec = spectrogram(samples, sample_rate, frame_length=8192)
    return float(spec.frequencies_hz[np.argmax(spec.mean_psd())])


class TestToFloat:
    def test_signed_integers_use_their_full_scale(self) -> None:
        np.testing.assert_array_equal(
            to_float(np.array([-32768, 0, 16384], dtype=np.int16)), [-1.0, 0.0, 0.5]
        )
        np.testing.assert_array_equal(
            to_float(np.array([-(2**31), 2**30], dtype=np.int32)), [-1.0, 0.5]
        )
        np.testing.assert_array_equal(to_float(np.array([-128, 64], dtype=np.int8)), [-1.0, 0.5])

    def test_unsigned_bytes_are_centred(self) -> None:
        np.testing.assert_array_equal(
            to_float(np.array([0, 128, 192], dtype=np.uint8)), [-1, 0, 0.5]
        )

    def test_floats_pass_through_as_float64(self) -> None:
        out = to_float(np.array([0.25, -0.5], dtype=np.float32))
        assert out.dtype == np.float64
        np.testing.assert_array_equal(out, [0.25, -0.5])

    @pytest.mark.parametrize("dtype", [np.uint16, np.complex64, np.bool_])
    def test_rejects_unsupported_types(self, dtype: type) -> None:
        with pytest.raises(TypeError, match="unsupported"):
            to_float(np.zeros(4, dtype=dtype))


class TestDownmix:
    def test_averages_channels(self) -> None:
        stereo = np.array([[1.0, -1.0], [0.5, 0.5]])
        np.testing.assert_array_equal(downmix(stereo), [0.0, 0.5])
        np.testing.assert_array_equal(downmix(stereo.T, channel_axis=0), [0.0, 0.5])

    def test_rejects_three_dimensions(self) -> None:
        with pytest.raises(ValueError, match="1-D or 2-D"):
            downmix(np.zeros((2, 2, 2)))


class TestResample:
    @pytest.mark.parametrize("from_rate", [16_000, 32_000, 44_100, 48_000, 96_000])
    def test_keeps_frequency_and_level_of_an_in_band_tone(self, from_rate: int) -> None:
        tone = sine(3_000.0, from_rate)
        out = resample(tone, from_rate)
        assert out.size == pytest.approx(2 * ANALYSIS_SAMPLE_RATE, abs=1)
        assert peak_frequency(out, ANALYSIS_SAMPLE_RATE) == pytest.approx(3_000.0, abs=3.0)
        # Skip the filter's start-up and tail transients when comparing levels.
        edge = ANALYSIS_SAMPLE_RATE // 10
        assert rms_dbfs(out[edge:-edge]) == pytest.approx(rms_dbfs(tone), abs=0.05)

    def test_removes_content_above_the_new_nyquist_frequency(self) -> None:
        out = resample(sine(15_000.0, 48_000), 48_000)
        assert rms_dbfs(out[2_000:-2_000]) < rms_dbfs(sine(15_000.0, 48_000)) - 40

    def test_same_rate_is_a_no_op(self) -> None:
        tone = sine(1_000.0, ANALYSIS_SAMPLE_RATE)
        assert resample(tone, ANALYSIS_SAMPLE_RATE) is tone

    def test_rejects_non_positive_rates(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            resample(np.zeros(10), 0)


class TestPrepare:
    def test_stereo_int16_at_48k_becomes_a_mono_float_frame(self) -> None:
        left = sine(2_000.0, 48_000, amplitude=0.5)
        stereo = (np.stack([left, left], axis=-1) * 32767).astype(np.int16)
        frame = prepare(stereo, 48_000)
        assert frame.sample_rate == ANALYSIS_SAMPLE_RATE
        assert frame.samples.dtype == np.float64
        assert frame.samples.ndim == 1
        assert frame.duration_s == pytest.approx(2.0, abs=1e-4)
        assert peak_frequency(frame.samples, frame.sample_rate) == pytest.approx(2_000.0, abs=3.0)

    def test_removes_and_reports_the_dc_offset(self) -> None:
        biased = sine(1_000.0, ANALYSIS_SAMPLE_RATE) + 0.1
        frame = prepare(biased, ANALYSIS_SAMPLE_RATE)
        assert frame.dc_offset == pytest.approx(0.1, abs=1e-3)
        assert abs(float(frame.samples.mean())) < 1e-12

    def test_dc_removal_can_be_turned_off(self) -> None:
        frame = prepare(np.full(100, 0.25), ANALYSIS_SAMPLE_RATE, remove_dc=False)
        assert frame.dc_offset == 0.0
        np.testing.assert_array_equal(frame.samples, 0.25)

    def test_rejects_empty_input(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            prepare(np.zeros(0), ANALYSIS_SAMPLE_RATE)

    @given(st.integers(0, 2**32 - 1))
    def test_is_deterministic(self, seed: int) -> None:
        noise = np.random.default_rng(seed).normal(0, 0.1, (4_800, 2))
        a, b = prepare(noise, 48_000), prepare(noise.copy(), 48_000)
        np.testing.assert_array_equal(a.samples, b.samples)
