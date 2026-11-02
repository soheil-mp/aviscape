import math

import numpy as np
import pytest

from aviscape_dsp import FULL_SCALE_SINE_RMS, rms, rms_dbfs

SR = 22_050
T = np.arange(SR) / SR  # one second: 1 kHz fits exactly 1000 cycles


def test_full_scale_sine_is_zero_dbfs() -> None:
    sine = np.sin(2 * np.pi * 1000.0 * T)
    assert rms(sine) == pytest.approx(FULL_SCALE_SINE_RMS, rel=1e-12)
    assert rms_dbfs(sine) == pytest.approx(0.0, abs=1e-9)


def test_half_amplitude_is_minus_six_dbfs() -> None:
    assert rms_dbfs(0.5 * np.sin(2 * np.pi * 1000.0 * T)) == pytest.approx(-6.0206, abs=1e-4)


def test_full_scale_square_is_plus_three_dbfs() -> None:
    square = np.sign(np.sin(2 * np.pi * 1000.0 * T + 0.1))
    assert rms_dbfs(square) == pytest.approx(3.0103, abs=1e-4)


def test_digital_silence_is_minus_infinity() -> None:
    assert rms_dbfs(np.zeros(100)) == -math.inf


def test_empty_signal_is_rejected() -> None:
    with pytest.raises(ValueError, match="empty"):
        rms([])
