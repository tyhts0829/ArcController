import math
import random
import types

import noise
import pytest

from controller.lfo_styles import (
    LFO_STYLE_MAP,
    PerlinLfoStyle,
    RandomLfoStyle,
    SawLfoStyle,
    SineLfoStyle,
    SquareLfoStyle,
    StaticLfoStyle,
    TriangleLfoStyle,
)
from enums.enums import LfoStyle


class DummyState:
    def __init__(self, current_value=0.0, lfo_frequency=1.0, lfo_amplitude=1.0):
        self.current_value = current_value
        self.lfo_frequency = lfo_frequency
        self.lfo_amplitude = lfo_amplitude


def test_static_lfo():
    state = DummyState(current_value=5.0)
    lfo = StaticLfoStyle()
    result = lfo.update(state, dt=0.5)
    assert result == 5.0


def test_random_lfo_monkeypatched(monkeypatch):
    state = DummyState(lfo_frequency=2.0)
    lfo = RandomLfoStyle()
    # force random.random() to return 0.75
    monkeypatch.setattr(random, "random", lambda: 0.75)
    jitter = lfo.update(state, dt=0.2)
    # jitter = (0.75 - 0.5) * frequency * dt = 0.25 * 2.0 * 0.2 = 0.1
    assert pytest.approx(jitter, rel=1e-6) == 0.1


def test_sine_lfo_phase_and_value():
    state = DummyState(lfo_frequency=1.0, lfo_amplitude=2.0)
    lfo = SineLfoStyle()
    # initial phase = 0.0
    value = lfo.update(state, dt=0.25)
    # phase -> 0.25, sin(2π*0.25) = 1.0, output = 2.0
    assert math.isclose(value, 2.0, rel_tol=1e-6)
    # phase wraps correctly
    lfo.phase = 0.9
    value2 = lfo.update(state, dt=0.2)
    # new phase -> (0.9 + 0.2) % 1.0 = 0.1, sin(2π*0.1)
    expected = 2.0 * math.sin(2 * math.pi * 0.1)
    assert math.isclose(value2, expected, rel_tol=1e-6)


@pytest.mark.parametrize(
    "strategy_class, phase_val, expected",
    [
        (SawLfoStyle, 0.25, lambda amp, ph: amp * (2 * ph - 1)),
        (SquareLfoStyle, 0.25, lambda amp, ph: amp if ph < 0.5 else -amp),
        (TriangleLfoStyle, 0.25, lambda amp, ph: amp * (4 * abs(ph - 0.5) - 1)),
    ],
)
def test_waveform_lfos(strategy_class, phase_val, expected):
    state = DummyState(lfo_frequency=1.0, lfo_amplitude=3.0)
    lfo = strategy_class()
    # set phase manually to control output
    lfo.phase = phase_val
    val = lfo.update(state, dt=0)
    assert val == pytest.approx(expected(3.0, phase_val), rel=1e-6)


def test_perlin_lfo_monkeypatched(monkeypatch):
    state = DummyState(lfo_frequency=0.5, lfo_amplitude=4.0)
    lfo = PerlinLfoStyle()
    # simulate pnoise1 returning 0.3
    monkeypatch.setattr(noise, "pnoise1", lambda x: 0.3)
    out1 = lfo.update(state, dt=0.2)
    # x increases: initial x = 0.0 -> 0.1, output = amplitude * 0.3
    assert pytest.approx(lfo.x, rel=1e-6) == 0.5 * 0.2
    assert pytest.approx(out1, rel=1e-6) == 4.0 * 0.3
    # update again to check accumulation
    out2 = lfo.update(state, dt=0.2)
    assert pytest.approx(lfo.x, rel=1e-6) == 0.5 * 0.4
    assert pytest.approx(out2, rel=1e-6) == 4.0 * 0.3


def test_factory_mapping():
    for style, factory in LFO_STYLE_MAP.items():
        instance = factory()
        # check instance type matches expected class
        class_name = style.name.title() + "Lfo"
        assert instance.__class__.__name__.lower() == class_name.lower()
    # also check coverage for all enum members
    all_styles = {s for s in LfoStyle}
    assert set(LFO_STYLE_MAP.keys()) == all_styles
