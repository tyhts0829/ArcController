"""
controller.led_styles
---------------------

LedStyle ごとに LED レベル配列を生成するクラス群。
"""

from __future__ import annotations

import logging
from typing import Dict, List, Type

from enums.enums import LedStyle, ValueStyle

LOGGER = logging.getLogger(__name__)


class _BaseStyleRenderer:
    """共通ヘルパの抽象基底"""

    TICKS = 64  # 1 リングの LED 数

    def __init__(self, max_brightness: int = 15):
        self.max_brightness = max_brightness

    # ----------------- public API -----------------
    def build_levels(self, value: float, vstyle: ValueStyle) -> List[int]:
        """64 要素 (0‒15) の輝度リストを返す"""
        raise NotImplementedError

    # ----------------- helper ---------------------
    def _value_to_pos(self, value: float, vstyle: ValueStyle) -> int:
        """ValueStyle → 0‒63 位置へマップ"""
        if vstyle == ValueStyle.LINEAR:
            norm = value
        elif vstyle == ValueStyle.BIPOLAR:
            norm = value + 0.5
        elif vstyle == ValueStyle.INFINITE:
            norm = value % 1.0
        elif vstyle == ValueStyle.MIDI_7BIT:
            norm = value / 127.0
        elif vstyle == ValueStyle.MIDI_14BIT:
            norm = value / 16383.0
        else:
            norm = 0.0
            LOGGER.warning("Unknown ValueStyle %s -> pos=0", vstyle)

        return int(norm * (self.TICKS - 1)) % self.TICKS


class DotRenderer(_BaseStyleRenderer):
    """LED 1 つだけ点灯"""

    def build_levels(self, value: float, vstyle: ValueStyle) -> List[int]:
        levels = [0] * self.TICKS
        pos = self._value_to_pos(value, vstyle)
        levels[pos] = self.max_brightness
        return levels


class PotentiometerRenderer(_BaseStyleRenderer):
    """ポテンショメータ表示 (0 から現在位置まで帯状)"""

    def build_levels(self, value: float, vstyle: ValueStyle) -> List[int]:
        levels = [0] * self.TICKS
        pos = self._value_to_pos(value, vstyle)
        for i in range(pos + 1):
            levels[i] = self.max_brightness
        return levels


class BipolarRenderer(_BaseStyleRenderer):
    """中央基準で左右に伸びる表示"""

    def build_levels(self, value: float, vstyle: ValueStyle) -> List[int]:
        levels = [0] * self.TICKS
        pos = self._value_to_pos(value, vstyle)
        center = self.TICKS // 2
        if pos >= center:
            rng = range(center, pos + 1)
        else:
            rng = range(pos, center)
        for i in rng:
            levels[i] = self.max_brightness
        # センター LED を薄く表示
        levels[center] = max(1, self.max_brightness // 4)
        return levels


# -----------------------------------------------------------------------------
# Factory
# -----------------------------------------------------------------------------
_RENDERER_MAP: Dict[LedStyle, Type[_BaseStyleRenderer]] = {
    LedStyle.DOT: DotRenderer,
    LedStyle.POTENTIOMETER: PotentiometerRenderer,
    LedStyle.BIPOLAR: BipolarRenderer,
}


def get_renderer(style: LedStyle, max_brightness: int = 15) -> _BaseStyleRenderer:
    cls = _RENDERER_MAP.get(style)
    if cls is None:
        LOGGER.warning("Unknown LedStyle %s – fallback to DOT", style)
        cls = DotRenderer
    return cls(max_brightness)
