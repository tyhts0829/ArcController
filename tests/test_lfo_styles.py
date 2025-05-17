import math
import sys
import types

import pytest

# Provide a stub noise module for import
sys.modules.setdefault("noise", types.SimpleNamespace(pnoise1=lambda x, base=0: 0.0))  # type: ignore

from lfo import lfo_styles
from src.model.model import RingState


def test_get_lfo_instance_types():
    """
    ファクトリが正しいクラスのインスタンスを返すことを確認するテスト。
    """
    for style_enum, cls in lfo_styles.LFO_STYLE_MAP.items():
        inst = lfo_styles.get_lfo_instance(style_enum)
        assert isinstance(inst, cls)


def test_static_lfo_returns_current_value():
    """StaticLfoStyle の update メソッドが RingState.current_value をそのまま返すことを確認するテスト。"""
    ring = RingState(current_value=0.75)
    lfo = lfo_styles.StaticLfoStyle()
    val = lfo.update(ring, 1.0)
    assert val == ring.current_value


def test_random_lfo_jitter(monkeypatch):
    """RandomLfoStyle の update メソッドが周波数に応じたジッター値を返すことを確認するテスト。

    monkeypatch で random.random() を固定し、期待値を決定論的に検証する。"""
    monkeypatch.setattr(lfo_styles.random, "random", lambda: 1.0)
    ring = RingState(lfo_frequency=0.2)
    lfo = lfo_styles.RandomLfoStyle()
    val = lfo.update(ring, 1.0)
    assert val == pytest.approx(0.1)


def test_sine_lfo_updates_phase_and_value():
    """SineLfoStyle の update メソッドが lfo_phase を更新し、サイン波に基づく値を返すことを確認するテスト。"""
    ring = RingState(lfo_frequency=0.25, lfo_amplitude=1.0)
    lfo = lfo_styles.SineLfoStyle()
    val = lfo.update(ring, 1.0)
    assert ring.lfo_phase == pytest.approx(0.25)
    assert val == pytest.approx(1.0)


def test_saw_lfo():
    """SawLfoStyle の update メソッドが lfo_phase を更新し、ノコギリ波に基づく値を返すことを確認するテスト。"""
    ring = RingState(lfo_frequency=0.25, lfo_amplitude=1.0)
    lfo = lfo_styles.SawLfoStyle()
    val = lfo.update(ring, 1.0)
    assert ring.lfo_phase == pytest.approx(0.25)
    assert val == pytest.approx(-0.5)


def test_square_lfo():
    """SquareLfoStyle の update メソッドが lfo_phase を更新し、矩形波に基づく値を返すことを確認するテスト。"""
    ring = RingState(lfo_frequency=0.25, lfo_amplitude=1.0)
    lfo = lfo_styles.SquareLfoStyle()
    val = lfo.update(ring, 1.0)
    assert ring.lfo_phase == pytest.approx(0.25)
    assert val == pytest.approx(1.0)


def test_triangle_lfo():
    """TriangleLfoStyle の update メソッドが lfo_phase を更新し、三角波に基づく値を返すことを確認するテスト。"""
    ring = RingState(lfo_frequency=0.25, lfo_amplitude=1.0)
    lfo = lfo_styles.TriangleLfoStyle()
    val = lfo.update(ring, 1.0)
    assert ring.lfo_phase == pytest.approx(0.25)
    assert val == pytest.approx(0.0)


def test_perlin_lfo(monkeypatch):
    """PerlinLfoStyle の update メソッドが lfo_phase を更新し、Perlin ノイズに基づく値を返すことを確認するテスト。

    monkeypatch で noise.pnoise1() を固定し、期待値を決定論的に検証する。"""
    monkeypatch.setattr(lfo_styles, "noise", types.SimpleNamespace(pnoise1=lambda x, base=0: 0.5))
    ring = RingState(lfo_frequency=0.25, lfo_amplitude=1.0, cc_number=1)
    lfo = lfo_styles.PerlinLfoStyle()
    val = lfo.update(ring, 1.0)
    assert ring.lfo_phase == pytest.approx(0.25)
    assert val == pytest.approx(0.5)
