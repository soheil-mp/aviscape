from datetime import UTC, datetime, timedelta, timezone

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from aviscape_synth import Tone, ToneNoiseSource

START = datetime(2026, 5, 1, 4, 30, tzinfo=UTC)


def make_source(**overrides: object) -> ToneNoiseSource:
    config: dict[str, object] = {
        "sensor_id": "synthetic-1",
        "seed": 7,
        "start": START,
        "tones": (Tone(3000.0, 0.25),),
        "noise_rms": 0.05,
        "window_s": 2,
    }
    config.update(overrides)
    return ToneNoiseSource(**config)  # type: ignore[arg-type]


def test_same_seed_gives_byte_identical_audio() -> None:
    first, second = make_source(), make_source()
    for index in (0, 3, 1000):
        assert first.window(index).samples.tobytes() == second.window(index).samples.tobytes()


def test_different_seeds_give_different_noise() -> None:
    a = make_source(seed=1).window(0).samples
    b = make_source(seed=2).window(0).samples
    assert not np.array_equal(a, b)


def test_window_shape_dtype_and_timing() -> None:
    source = make_source()
    window = source.window(5)
    assert window.samples.dtype == np.float32
    assert window.samples.shape == (source.sample_rate * 2,)
    assert window.duration_s == 2
    assert window.start == START + timedelta(seconds=10)
    assert window.sensor_id == "synthetic-1"


def test_tones_are_phase_continuous_across_windows() -> None:
    source = make_source(noise_rms=0.0, window_s=1)
    joined = np.concatenate([source.window(0).samples, source.window(1).samples])
    t = np.arange(joined.size) / source.sample_rate
    expected = 0.25 * np.sin(2 * np.pi * 3000.0 * t)
    np.testing.assert_allclose(joined, expected, atol=1e-6)


def test_tone_appears_at_its_frequency() -> None:
    source = make_source(noise_rms=0.01, window_s=1)
    samples = source.window(0).samples
    spectrum = np.abs(np.fft.rfft(samples))
    peak_hz = np.argmax(spectrum) * source.sample_rate / samples.size
    assert peak_hz == pytest.approx(3000.0, abs=1.0)


def test_noise_has_the_requested_rms() -> None:
    samples = make_source(tones=(), noise_rms=0.1, window_s=10).window(0).samples
    assert float(np.sqrt(np.mean(samples.astype(np.float64) ** 2))) == pytest.approx(0.1, rel=0.01)


def test_silence_without_tones_or_noise() -> None:
    assert not np.any(make_source(tones=(), noise_rms=0.0).window(0).samples)


def test_windows_without_speed_never_sleep() -> None:
    calls: list[float] = []
    windows = list(make_source().windows(3, sleep=calls.append))
    assert [w.start for w in windows] == [START + timedelta(seconds=2 * i) for i in range(3)]
    assert calls == []


def test_windows_are_paced_by_speed() -> None:
    calls: list[float] = []
    list(make_source(window_s=60).windows(4, speed=60.0, sleep=calls.append))
    assert calls == [1.0, 1.0, 1.0]


def test_windows_without_count_continue_indefinitely() -> None:
    iterator = make_source().windows()
    assert [next(iterator).start for _ in range(5)][-1] == START + timedelta(seconds=8)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"seed": -1}, "seed"),
        ({"start": datetime(2026, 5, 1, 4, 30)}, "timezone-aware"),  # noqa: DTZ001
        ({"start": START + timedelta(seconds=1)}, "aligned"),
        ({"tones": (Tone(11025.0, 0.1),)}, "Nyquist"),
        ({"tones": (Tone(1000.0, 0.6), Tone(2000.0, 0.6))}, "add up"),
        ({"noise_rms": -0.1}, "noise_rms"),
        ({"window_s": 0}, "positive"),
    ],
)
def test_invalid_configuration_is_rejected(overrides: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        make_source(**overrides)


@pytest.mark.parametrize(
    ("frequency", "amplitude", "message"),
    [(0.0, 0.5, "frequency"), (1000.0, 1.5, "amplitude"), (1000.0, -0.1, "amplitude")],
)
def test_invalid_tone_is_rejected(frequency: float, amplitude: float, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        Tone(frequency, amplitude)


def test_invalid_index_and_speed_are_rejected() -> None:
    source = make_source()
    with pytest.raises(ValueError, match="index"):
        source.window(-1)
    with pytest.raises(ValueError, match="speed"):
        next(source.windows(1, speed=0.0))


def test_non_utc_timezones_are_accepted_when_aligned() -> None:
    cest = timezone(timedelta(hours=2))
    source = make_source(start=datetime(2026, 5, 1, 6, 30, tzinfo=cest))
    assert source.window(0).start.utcoffset() == timedelta(hours=2)


@given(
    seed=st.integers(min_value=0, max_value=2**63 - 1),
    index=st.integers(min_value=0, max_value=10**6),
    noise_rms=st.floats(min_value=0.0, max_value=0.3),
)
def test_windows_are_always_finite_float32_of_fixed_length(
    seed: int, index: int, noise_rms: float
) -> None:
    source = make_source(seed=seed, noise_rms=noise_rms, window_s=1)
    samples = source.window(index).samples
    assert samples.dtype == np.float32
    assert samples.size == source.samples_per_window
    assert np.all(np.isfinite(samples))
