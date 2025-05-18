from src.model.model import Model, RingState
from src.enums.enums import ValueStyle, LedStyle, LfoStyle


def test_apply_delta_clamps_linear():
    """apply_delta() が LINEAR スタイルで 0.0-1.0 に丸めるか確認する"""
    ring = RingState(current_value=0.9, value_style=ValueStyle.LINEAR)
    ring.apply_delta(200)
    assert ring.current_value == 1.0


def test_apply_lfo_delta_clamps_range():
    """apply_lfo_delta() が 0.0-1.0 範囲に収めるか確認する"""
    ring = RingState(lfo_frequency=0.95)
    ring.apply_lfo_delta(200)
    assert ring.lfo_frequency == 1.0
    ring.lfo_frequency = 0.05
    ring.apply_lfo_delta(-200)
    assert ring.lfo_frequency == 0.0


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

