"""Tests for LED style classes in src.renderer.led_styles."""

from src.enums.enums import ValueStyle
from src.renderer.led_styles import BipolarStyle, DotStyle, PotentiometerStyle

MAX_BRIGHTNESS = 10  # Match the value used in config.yaml


def test_dotstyle_interpolation_half_brightness():
    """DotStyle: halfway between two LEDs splits brightness equally."""
    style = DotStyle(max_brightness=MAX_BRIGHTNESS, tail_decay=1.0)

    # Value exactly midway between LED16 and LED17 (16.5 / 64)
    levels = style.build_levels(16.5 / 64.0, ValueStyle.LINEAR).copy()

    half = int(round(MAX_BRIGHTNESS * 0.5))
    assert levels[16] == half
    assert levels[17] == half
    # No other LEDs should be lit
    lit_indices = [i for i, b in enumerate(levels) if b > 0]
    assert set(lit_indices) == {16, 17}


def test_potentiometer_zero_and_full_scale():
    """PotentiometerStyle: edge cases at 0.0 and 1.0."""
    style = PotentiometerStyle(max_brightness=MAX_BRIGHTNESS)

    # value = 0.0 → only LED40 should be lit with brightness 1
    levels_zero = style.build_levels(0.0, ValueStyle.LINEAR).copy()
    assert levels_zero[40] == 1
    assert sum(levels_zero) == 1  # only one LED lit

    # value = 1.0 → LED24 should be max brightness, LED40 should be 1
    levels_full = style.build_levels(1.0, ValueStyle.LINEAR).copy()
    assert levels_full[24] == MAX_BRIGHTNESS
    assert levels_full[40] == 1

    # Brightness should be non‑decreasing from LED40 to LED24 along the arc
    arc_indices = style._arc_indices  # pylint: disable=protected-access
    brightness_values = [levels_full[i] for i in arc_indices]
    assert all(x <= y for x, y in zip(brightness_values, brightness_values[1:]))


def test_bipolar_span_positive_and_negative():
    """BipolarStyle: span reaches correct ends and uses expected dim level."""
    style = BipolarStyle(max_brightness=MAX_BRIGHTNESS)
    dim = max(1, MAX_BRIGHTNESS // 4)

    # Positive half‑range
    levels_pos = style.build_levels(0.5, ValueStyle.BIPOLAR).copy()
    assert levels_pos[0] == MAX_BRIGHTNESS  # Center LED
    assert levels_pos[21] == dim  # Right‑down end

    # Negative half‑range
    levels_neg = style.build_levels(-0.5, ValueStyle.BIPOLAR).copy()
    assert levels_neg[0] == MAX_BRIGHTNESS
    assert levels_neg[43] == dim
