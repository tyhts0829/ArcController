"""
Comprehensive unit tests for core data‑model logic.

Targets:
* RingState.apply_delta / apply_lfo_delta / cycle_preset
* Model.cycle_layer
"""

import logging

import pytest

from src.enums.enums import ValueStyle
from src.model.model import Model, RingState


# ----------------------------------------------------------------------
# RingState.apply_delta – basic LINEAR clamp (legacy sanity check)
# ----------------------------------------------------------------------
def test_apply_delta_clamps_linear():
    """LINEAR スタイルで 0.0‒1.0 にクランプされるか"""
    ring = RingState(current_value=0.9, value_style=ValueStyle.LINEAR)
    ring.apply_delta(200)  # +0.2
    assert ring.current_value == 1.0


# ----------------------------------------------------------------------
# RingState.apply_lfo_delta – basic range clamp (legacy sanity check)
# ----------------------------------------------------------------------
def test_apply_lfo_delta_clamps_range():
    """0.0‒1.0 にクランプされるか"""
    ring = RingState(lfo_frequency=0.95)
    ring.apply_lfo_delta(200)  # +0.1 → clamp
    assert ring.lfo_frequency == 1.0
    ring.lfo_frequency = 0.05
    ring.apply_lfo_delta(-200)  # -0.1 → clamp
    assert ring.lfo_frequency == 0.0


# ----------------------------------------------------------------------
# RingState.apply_delta – exhaustive style / boundary coverage
# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    "style,start,delta,expected",
    [
        # LINEAR  : clamp 上下限
        (ValueStyle.LINEAR, 0.1, 10_000, 1.0),  # 上限
        (ValueStyle.LINEAR, 0.9, -10_000, 0.0),  # 下限
        # BIPOLAR : clamp 0.0-1.0 (現在の実装では全て0.0-1.0範囲)
        (ValueStyle.BIPOLAR, 0.0, 10_000, 1.0),
        (ValueStyle.BIPOLAR, 0.0, -10_000, 0.0),
        # INFINITE: 制限なし（増分 = delta * value_gain）
        (ValueStyle.INFINITE, 0.0, 12_345, pytest.approx(12.345)),
        # MIDI 7‑bit: clamp 0.0-1.0 (現在の実装では全て0.0-1.0範囲)
        (ValueStyle.MIDI_7BIT, 0.12, 100_000, 1.0),
        # MIDI 14‑bit: clamp 0.0-1.0 (現在の実装では全て0.0-1.0範囲)
        (ValueStyle.MIDI_14BIT, 0.16, 1_000_000, 1.0),
    ],
)
def test_apply_delta_all_styles(style, start, delta, expected):
    """すべての ValueStyle で境界値が期待通りか検証"""
    ring = RingState(current_value=start, value_style=style)
    ring.apply_delta(delta)
    assert ring.current_value == expected


# ----------------------------------------------------------------------
# RingState.apply_lfo_delta – gain factor & clamp
# ----------------------------------------------------------------------
def test_apply_lfo_delta_gain_and_clamp():
    """lfo_freq_gain が反映され、かつ 0.0‒1.0 にクランプされるか"""
    ring = RingState(lfo_frequency=0.4, lfo_freq_gain=0.01)
    ring.apply_lfo_delta(50)  # +0.5
    assert ring.lfo_frequency == pytest.approx(0.9)
    ring.apply_lfo_delta(20_000)  # 大幅オーバー → clamp=1.0
    assert ring.lfo_frequency == 1.0


# ----------------------------------------------------------------------
# RingState.cycle_preset – wrapping & warnings
# ----------------------------------------------------------------------
def test_cycle_preset_negative_wrap():
    """負方向ステップで underflow wrap するか"""
    presets = [{"value_style": "linear", "led_style": "dot", "lfo_style": "static"}] * 3
    ring = RingState()
    ring.set_presets(presets)
    ring.cycle_preset(-1)
    assert ring.preset_index == len(presets) - 1


def test_cycle_preset_empty_warn(caplog):
    """プリセット空時に warning が出るか"""
    caplog.set_level(logging.WARNING)
    ring = RingState()
    ring.cycle_preset(1)
    assert "Preset list is empty" in caplog.text


# ----------------------------------------------------------------------
# Model.cycle_layer – arbitrary step & wrap
# ----------------------------------------------------------------------
@pytest.mark.parametrize("step", [2, -1, 8])
def test_cycle_layer_various_steps(step):
    """±step で active_layer_idx が循環するか"""
    model = Model()
    initial = model.active_layer_idx
    model.cycle_layer(step)
    expected = (initial + step) % len(model.layers)
    assert model.active_layer_idx == expected


def test_cycle_preset_updates_attributes():
    """cycle_preset() で次のプリセットが適用されることを確認する"""
    ring = RingState()
    presets = [
        {"value_style": "linear", "led_style": "dot", "lfo_style": "static"},
        {"value_style": "bipolar", "led_style": "bipolar", "lfo_style": "static"},
    ]
    ring.set_presets(presets)
    ring.apply_preset(presets[0])
    ring.cycle_preset(1)
    assert ring.preset_index == 1
    assert ring.value_style == ValueStyle.BIPOLAR


def test_model_cycle_layer_wraps():
    """Model.cycle_layer() がインデックスを循環させるか確認する"""
    model = Model()
    model.active_layer_idx = len(model.layers) - 1
    model.cycle_layer(1)
    assert model.active_layer_idx == 0
