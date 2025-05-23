"""Tests for deterministic LFO style classes in src.lfo.lfo_styles."""

import math

import pytest

from src.model.model import RingState
from src.services.lfo.lfo_styles import (
    SawLfoStyle,
    SineLfoStyle,
    SquareLfoStyle,
    StaticLfoStyle,
    TriangleLfoStyle,
)


def test_static_lfo_returns_current_value():
    """StaticLfoStyle should echo `current_value` without mutating the phase."""
    ring = RingState(value=0.123, lfo_amplitude=0.9)
    style = StaticLfoStyle()

    out = style.update(ring, dt=1.0)

    assert out == pytest.approx(0.123)
    # phase remains unchanged (default 0.0)
    assert ring.lfo_phase == 0.0


def test_sine_lfo_phase_and_value():
    """SineLfoStyle advances phase correctly and returns sin value."""
    ring = RingState(lfo_frequency=1.0, lfo_amplitude=1.0, lfo_phase=0.0)
    style = SineLfoStyle()

    out = style.update(ring, dt=0.25)  # phase -> 0.25

    assert ring.lfo_phase == pytest.approx(0.25)
    assert out == pytest.approx(1.0)


def test_sine_lfo_phase_wrap():
    """Phase should wrap into [0,1) after exceeding 1.0."""
    ring = RingState(lfo_frequency=1.0, lfo_amplitude=1.0, lfo_phase=0.9)
    style = SineLfoStyle()

    out = style.update(ring, dt=0.2)  # phase -> (0.9+0.2) % 1 = 0.1
    expected = math.sin(2 * math.pi * 0.1)

    assert ring.lfo_phase == pytest.approx(0.1)
    assert out == pytest.approx(expected)


def test_saw_lfo_value():
    """SawLfoStyle should produce a linear ramp from -amp to +amp."""
    ring = RingState(lfo_frequency=1.0, lfo_amplitude=1.0, lfo_phase=0.0)
    style = SawLfoStyle()

    out = style.update(ring, dt=0.25)  # phase -> 0.25
    expected = 2 * 0.25 - 1  # -0.5

    assert out == pytest.approx(expected)


def test_square_lfo_toggle():
    """SquareLfoStyle toggles sign when phase crosses 0.5."""
    ring = RingState(lfo_frequency=1.0, lfo_amplitude=0.8, lfo_phase=0.4)
    style = SquareLfoStyle()

    out = style.update(ring, dt=0.2)  # phase -> 0.6 (>0.5) -> -amp

    assert ring.lfo_phase == pytest.approx(0.6)
    assert out == pytest.approx(-0.8)


@pytest.mark.parametrize(
    "phase,expected",
    [
        (0.0, 1.0),  # triangle peaks at -amp when phase == 0 or 1 -> tri = -1
        (0.25, 0.0),  # center rising edge
        (0.5, -1.0),  # trough
        (0.75, 0.0),  # center falling edge
    ],
)
def test_triangle_lfo_shape(phase, expected):
    """TriangleLfoStyle produces the expected piece‑wise linear waveform."""
    amp = 1.0
    ring = RingState(lfo_frequency=0.0, lfo_amplitude=amp, lfo_phase=phase)
    style = TriangleLfoStyle()

    # dt=0 so phase stays; we're sampling waveform directly
    out = style.update(ring, dt=0.0)

    assert out == pytest.approx(amp * expected)
