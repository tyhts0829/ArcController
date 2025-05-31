"""Tests for LED style classes in arc.services.renderers.led_styles."""

from arc.services.renderers.led_styles import (
    BipolarStyle,
    DotStyle,
    PotentiometerStyle,
    PerlinLedStyle,
    LED_STYLE_MAP,
    get_led_instance,
)

from arc.enums.enums import LedStyle, ValueStyle

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


def test_style_enum_instance_method():
    """Test that style_enum() instance method returns correct enum for each style."""
    # Create instances of each style
    dot_style = DotStyle(max_brightness=MAX_BRIGHTNESS)
    pot_style = PotentiometerStyle(max_brightness=MAX_BRIGHTNESS)
    bipolar_style = BipolarStyle(max_brightness=MAX_BRIGHTNESS)
    perlin_style = PerlinLedStyle(max_brightness=MAX_BRIGHTNESS)
    
    # Test style_enum() returns correct enum
    assert dot_style.style_enum() == LedStyle.DOT
    assert pot_style.style_enum() == LedStyle.POTENTIOMETER
    assert bipolar_style.style_enum() == LedStyle.BIPOLAR
    assert perlin_style.style_enum() == LedStyle.PERLIN


def test_led_style_map_correctness():
    """Test that LED_STYLE_MAP contains all LedStyle enums mapped to correct classes."""
    # Verify all enums are in the map
    assert set(LED_STYLE_MAP.keys()) == {
        LedStyle.DOT,
        LedStyle.POTENTIOMETER,
        LedStyle.BIPOLAR,
        LedStyle.PERLIN,
    }
    
    # Verify correct class mappings
    assert LED_STYLE_MAP[LedStyle.DOT] == DotStyle
    assert LED_STYLE_MAP[LedStyle.POTENTIOMETER] == PotentiometerStyle
    assert LED_STYLE_MAP[LedStyle.BIPOLAR] == BipolarStyle
    assert LED_STYLE_MAP[LedStyle.PERLIN] == PerlinLedStyle
    
    # Verify get_led_instance factory function
    for led_style, expected_class in LED_STYLE_MAP.items():
        instance = get_led_instance(led_style, max_brightness=MAX_BRIGHTNESS)
        assert isinstance(instance, expected_class)
        assert instance.max_brightness == MAX_BRIGHTNESS


def test_style_classmethod():
    """Test that each style class has a style() classmethod returning correct enum."""
    # Test each style class's classmethod
    assert DotStyle.style() == LedStyle.DOT
    assert PotentiometerStyle.style() == LedStyle.POTENTIOMETER
    assert BipolarStyle.style() == LedStyle.BIPOLAR
    assert PerlinLedStyle.style() == LedStyle.PERLIN
    
    # Verify the relationship between classmethod and instance method
    styles = [
        (DotStyle, LedStyle.DOT),
        (PotentiometerStyle, LedStyle.POTENTIOMETER),
        (BipolarStyle, LedStyle.BIPOLAR),
        (PerlinLedStyle, LedStyle.PERLIN),
    ]
    
    for style_class, expected_enum in styles:
        # Class method should return enum
        assert style_class.style() == expected_enum
        
        # Instance method should return same enum
        instance = style_class(max_brightness=MAX_BRIGHTNESS)
        assert instance.style_enum() == expected_enum
        
        # style_enum() should use the class's style() method
        assert instance.style_enum() == instance.__class__.style()
