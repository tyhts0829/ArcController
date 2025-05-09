"""
controller.led_styles
---------------------

LedStyle ごとに LED レベル配列を生成するクラス群。
"""

from __future__ import annotations

import logging
import math
import random
from typing import Dict, List, Type

import noise

from enums.enums import LedStyle, ValueStyle
from util.util import clamp

LOGGER = logging.getLogger(__name__)


class _BaseStyle:
    """共通ヘルパの抽象基底"""

    TICKS = 64  # 1 リングの LED 数

    def __init__(self, max_brightness: int = 15):
        self.max_brightness = max_brightness
        # 64 要素の輝度配列を一度だけ確保して再利用することで
        # 毎フレームの GC コストを下げる
        self._levels: List[int] = [0] * self.TICKS

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


class DotStyle(_BaseStyle):
    """LED 1 つだけ点灯"""

    def build_levels(self, value: float, vstyle: ValueStyle) -> List[int]:
        levels = self._levels
        # 既存リストを再利用しつつ全要素を 0 クリア
        levels[:] = [0] * self.TICKS
        pos = self._value_to_pos(value, vstyle)
        levels[pos] = self.max_brightness
        return levels


class PotentiometerStyle(_BaseStyle):
    """ポテンショメータ表示 (0 から現在位置まで帯状)"""

    def build_levels(self, value: float, vstyle: ValueStyle) -> List[int]:
        levels = self._levels
        levels[:] = [0] * self.TICKS
        pos = self._value_to_pos(value, vstyle)
        for i in range(pos + 1):
            levels[i] = self.max_brightness
        return levels


class BipolarStyle(_BaseStyle):
    """中央基準で左右に伸びる表示"""

    def build_levels(self, value: float, vstyle: ValueStyle) -> List[int]:
        levels = self._levels
        levels[:] = [0] * self.TICKS
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


class PerlinRenderer(_BaseStyle):
    """Perlin ノイズ空間を使って LED を揺らす表示"""

    # ---------------------- パラメータ定数 ----------------------
    PHI = (1 + math.sqrt(5)) / 2  # 黄金比
    MINIMUM_NOISE_RADIUS = PHI / 2.0
    NOISE_RADIUS_SCALE = 10.0
    MOVE_SPEED = 0.1
    NOISE_POSITION_INCREMENT = 0.02
    NOISE_POSITION_Y_SCALE = 0.3
    BRIGHTNESS_SCALE = 2.0
    BRIGHTNESS_OFFSET = 0.5
    _COS_TABLE = [math.cos(math.tau * i / _BaseStyle.TICKS) for i in range(_BaseStyle.TICKS)]
    _SIN_TABLE = [math.sin(math.tau * i / _BaseStyle.TICKS) for i in range(_BaseStyle.TICKS)]

    def __init__(self, max_brightness: int = 15) -> None:
        super().__init__(max_brightness)
        self.noise_position = 0.0
        self.noise_seed = random.randint(0, 100)
        self.previous_value = 0.0

    # --------------------- private helper ---------------------
    def _update_noise_position(self, value: float) -> None:
        """value 変化に応じてノイズ空間の走査位置を進める"""
        if value != self.previous_value:
            self.noise_position += value * self.MOVE_SPEED + self.NOISE_POSITION_INCREMENT
        self.previous_value = value

    def _noise_to_brightness(self, n: float) -> int:
        """Perlin ノイズ値 (-1..1) を 0‒max にマッピング"""
        raw = (n * self.BRIGHTNESS_SCALE + self.BRIGHTNESS_OFFSET) * self.max_brightness
        return clamp(int(raw), 0, self.max_brightness)

    # --------------------- public interface -------------------
    def build_levels(self, value: float, vstyle: ValueStyle) -> List[int]:
        """64 個の輝度レベルを返すメイン関数"""
        levels = self._levels
        levels[:] = [0] * self.TICKS

        # ノイズ円半径と走査位置を更新
        radius = self.MINIMUM_NOISE_RADIUS + value * self.NOISE_RADIUS_SCALE
        self._update_noise_position(value)

        # LED ごとに輝度計算 (③ coords 計算をインライン化 + テーブル参照)
        pos = self.noise_position
        y_scale = self.NOISE_POSITION_Y_SCALE * pos
        for i in range(self.TICKS):
            nx = radius * self._COS_TABLE[i] + pos
            ny = radius * self._SIN_TABLE[i] + y_scale
            n = noise.pnoise2(nx, ny, base=self.noise_seed)
            levels[i] = self._noise_to_brightness(n)

        return levels


# -----------------------------------------------------------------------------
# Factory
# -----------------------------------------------------------------------------
_RENDERER_MAP: Dict[LedStyle, Type[_BaseStyle]] = {
    LedStyle.DOT: DotStyle,
    LedStyle.POTENTIOMETER: PotentiometerStyle,
    LedStyle.BIPOLAR: BipolarStyle,
    LedStyle.PERLIN: PerlinRenderer,
}


def get_renderer(style: LedStyle, max_brightness: int = 15) -> _BaseStyle:
    cls = _RENDERER_MAP.get(style)
    if cls is None:
        LOGGER.warning("Unknown LedStyle %s – fallback to DOT", style)
        cls = DotStyle
    return cls(max_brightness)
