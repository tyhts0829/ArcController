"""Tests for LedRenderer._build_levels internal helper.

These tests focus on:
1. Style‑change detection & re‑instantiation cache.
2. Basic structural properties of the returned levels array.
"""

from src.enums.enums import LedStyle, ValueStyle
from src.model.model import RingState
from src.services.renderer.led_renderer import LedRenderer


def test_build_levels_reinstantiates_style():
    """_build_levels should create a new style instance when led_style changes."""
    renderer = LedRenderer(max_brightness=10)

    # First call with DOT style
    rs = RingState(led_style=LedStyle.DOT, value_style=ValueStyle.LINEAR, value=0.0)
    levels_first = renderer._build_levels(0, rs)  # pylint: disable=protected-access
    style_first = renderer._styles[0]  # pylint: disable=protected-access

    assert style_first.style_enum() is LedStyle.DOT
    assert len(levels_first) == 64

    # Change to POTENTIOMETER style and call again
    rs.led_style = LedStyle.POTENTIOMETER
    levels_second = renderer._build_levels(0, rs)  # pylint: disable=protected-access
    style_second = renderer._styles[0]  # pylint: disable=protected-access

    # Instance should be re‑created with a different id and class
    assert style_second.style_enum() is LedStyle.POTENTIOMETER
    assert style_first is not style_second
    assert len(levels_second) == 64


def test_build_levels_returns_64_ints():
    """Returned level list must contain 64 ints within [0, max_brightness]."""
    max_brightness = 10
    renderer = LedRenderer(max_brightness=max_brightness)
    rs = RingState(led_style=LedStyle.BIPOLAR, value_style=ValueStyle.BIPOLAR, value=0.0)

    levels = renderer._build_levels(0, rs)  # pylint: disable=protected-access

    assert len(levels) == 64
    assert all(isinstance(x, int) for x in levels)
    assert all(0 <= x <= max_brightness for x in levels)
