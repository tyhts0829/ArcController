"""
pytest test suite for ValueProcessor.apply()

実行方法:
    poetry run pytest      # or simply `pytest -q` if venv is active
"""

import math

import pytest

from controller.value_processor import ValueProcessor
from enums.enums import ValueStyle
from model.model import RingState


def make_ring(style: ValueStyle, value: float):
    """ヘルパー: 指定スタイルで RingState を簡易生成"""
    return RingState(current_value=value, value_style=style)


vp = ValueProcessor()


@pytest.mark.parametrize(
    "delta,start,expected",
    [
        (1000, 0.0, 1.0),  # clamp 上限
        (-2000, 1.0, 0.0),  # clamp 下限
    ],
)
def test_linear_clamp(delta, start, expected):
    rs = make_ring(ValueStyle.LINEAR, start)
    assert math.isclose(vp.update(delta, rs), expected, rel_tol=1e-6)


def test_linear_increment():
    rs = make_ring(ValueStyle.LINEAR, 0.5)
    new = vp.update(delta=100, ring_state=rs)  # 0.5 + 0.1
    assert math.isclose(new, 0.6, rel_tol=1e-6)


def test_bipolar_increment():
    rs = make_ring(ValueStyle.BIPOLAR, 0.0)
    new = vp.update(delta=-100, ring_state=rs)  # 0.0 − 0.1
    assert math.isclose(new, -0.1, rel_tol=1e-6)


def test_infinite():
    rs = make_ring(ValueStyle.INFINITE, 10.0)
    assert vp.update(delta=-5, ring_state=rs) == 5.0


def test_midi7bit_clamp():
    rs = make_ring(ValueStyle.MIDI_7BIT, 120)
    assert vp.update(delta=10, ring_state=rs) == 127  # clamp


def test_midi14bit():
    rs = make_ring(ValueStyle.MIDI_14BIT, 16000)
    assert vp.update(delta=200, ring_state=rs) == 16200  # within 16383
