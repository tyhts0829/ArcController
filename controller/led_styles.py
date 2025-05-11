"""
controller.led_styles
---------------------

LedStyle ごとに LED レベル配列を生成するクラス群。
"""

from __future__ import annotations

import logging
import math
import random
from abc import ABC, abstractmethod
from functools import cached_property
from typing import Type

import noise

from enums.enums import LedStyle, ValueStyle
from util.hardware_spec import ARC_SPEC, ArcSpec
from util.util import clamp

LOGGER = logging.getLogger(__name__)


class BaseLedStyle(ABC):
    """共通ヘルパの抽象基底"""

    def __init__(self, max_brightness: int, spec: ArcSpec = ARC_SPEC):
        self.max_brightness = max_brightness
        self.spec = spec
        # 64 要素の輝度配列を一度だけ確保して再利用することで
        # 毎フレームの GC コストを下げる
        self._levels: list[int] = [0] * self.spec.leds_per_ring

    # ----------------- public API -----------------
    @abstractmethod
    def build_levels(self, value: float, style: ValueStyle) -> list[int]:
        """64 要素 (0‒15) の輝度リストを返す"""
        raise NotImplementedError

    # ----------------- helper ---------------------
    def _value_to_pos(self, value: float, style: ValueStyle) -> int:
        """ValueStyle → 0‒63 位置へマップ"""
        if style == ValueStyle.LINEAR:
            norm = value
        elif style == ValueStyle.BIPOLAR:
            norm = value + 0.5
        elif style == ValueStyle.INFINITE:
            norm = value % 1.0
        elif style == ValueStyle.MIDI_7BIT:
            norm = value / 127.0
        elif style == ValueStyle.MIDI_14BIT:
            norm = value / 16383.0
        else:
            norm = 0.0
            LOGGER.warning("Unknown ValueStyle %s -> pos=0", style)

        return int(norm * (self.spec.leds_per_ring - 1)) % self.spec.leds_per_ring

    # ----------------- meta ---------------------
    @cached_property
    def style_enum(self) -> LedStyle | str:
        """
        自身のクラスに対応する LedStyle を返す。
        未登録の場合はクラス名文字列を返す。
        """
        return LED_CLASS_TO_STYLE_ENUM.get(self.__class__, self.__class__.__name__)


class DotStyle(BaseLedStyle):
    """LED 1 つだけ点灯"""

    def build_levels(self, value: float, style: ValueStyle) -> list[int]:
        levels = self._levels
        # 既存リストを再利用しつつ全要素を 0 クリア
        levels[:] = [0] * self.spec.leds_per_ring
        pos = self._value_to_pos(value, style)
        levels[pos] = self.max_brightness
        return levels


class PotentiometerStyle(BaseLedStyle):
    """ポテンショメータ表示 (0 から現在位置まで帯状)"""

    def build_levels(self, value: float, style: ValueStyle) -> list[int]:
        levels = self._levels
        levels[:] = [0] * self.spec.leds_per_ring
        pos = self._value_to_pos(value, style)
        for i in range(pos + 1):
            levels[i] = self.max_brightness
        return levels


class BipolarStyle(BaseLedStyle):
    """中央基準で左右に伸びる表示"""

    def build_levels(self, value: float, style: ValueStyle) -> list[int]:
        levels = self._levels
        levels[:] = [0] * self.spec.leds_per_ring
        pos = self._value_to_pos(value, style)
        center = self.spec.leds_per_ring // 2
        if pos >= center:
            rng = range(center, pos + 1)
        else:
            rng = range(pos, center)
        for i in rng:
            levels[i] = self.max_brightness
        # センター LED を薄く表示
        levels[center] = max(1, self.max_brightness // 4)
        return levels


class PerlinLedStyle(BaseLedStyle):
    """Perlin ノイズ空間を使って LED を揺らす表示"""

    # ---------------------- パラメータ定数 ----------------------
    PHI = (1 + math.sqrt(5)) / 2  # 黄金比
    MINIMUM_NOISE_RADIUS = PHI / 2.0
    NOISE_RADIUS_SCALE = 10.0
    MOVE_SPEED = 0.1
    NOISE_POSITION_INCREMENT = 0.01
    NOISE_POSITION_Y_SCALE = 0.3
    BRIGHTNESS_SCALE = 2.0
    BRIGHTNESS_OFFSET = 0.5
    _COS_TABLE = [math.cos(math.tau * i / ARC_SPEC.leds_per_ring) for i in range(ARC_SPEC.leds_per_ring)]
    _SIN_TABLE = [math.sin(math.tau * i / ARC_SPEC.leds_per_ring) for i in range(ARC_SPEC.leds_per_ring)]

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
    def build_levels(self, value: float, style: ValueStyle) -> list[int]:
        """64 個の輝度レベルを返すメイン関数"""
        levels = self._levels
        levels[:] = [0] * self.spec.leds_per_ring

        # ノイズ円半径と走査位置を更新
        radius = self.MINIMUM_NOISE_RADIUS + value * self.NOISE_RADIUS_SCALE
        self._update_noise_position(value)

        # LED ごとに輝度計算 (③ coords 計算をインライン化 + テーブル参照)
        pos = self.noise_position
        y_scale = self.NOISE_POSITION_Y_SCALE * pos
        for i in range(self.spec.leds_per_ring):
            nx = radius * self._COS_TABLE[i] + pos
            ny = radius * self._SIN_TABLE[i] + y_scale
            n = noise.pnoise2(nx, ny, base=self.noise_seed)
            levels[i] = self._noise_to_brightness(n)

        if pos > 1e4:
            # オーバーフロー防止
            self.noise_position = 0.0

        return levels


# -----------------------------------------------------------------------------
# Factory
# -----------------------------------------------------------------------------
LED_STYLE_MAP: dict[LedStyle, Type[BaseLedStyle]] = {
    LedStyle.DOT: DotStyle,
    LedStyle.POTENTIOMETER: PotentiometerStyle,
    LedStyle.BIPOLAR: BipolarStyle,
    LedStyle.PERLIN: PerlinLedStyle,
}

# 逆引き: クラス → LedStyle
LED_CLASS_TO_STYLE_ENUM: dict[type[BaseLedStyle], LedStyle] = {v: k for k, v in LED_STYLE_MAP.items()}


def get_led_instance(style: LedStyle, max_brightness: int = 15) -> BaseLedStyle:
    cls = LED_STYLE_MAP.get(style)
    if cls is None:
        LOGGER.warning("Unknown LedStyle %s – fallback to DOT", style)
        cls = DotStyle
    return cls(max_brightness)
