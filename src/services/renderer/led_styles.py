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
from typing import Type

import noise
import numpy as np

from src.enums.enums import LedStyle, ValueStyle
from src.utils.hardware_spec import ARC_SPEC, ArcSpec
from src.utils.util import clamp

LOGGER = logging.getLogger(__name__)


class BaseLedStyle(ABC):
    """共通ヘルパの抽象基底"""

    def __init__(self, max_brightness: int, spec: ArcSpec = ARC_SPEC):
        self.max_brightness = max_brightness
        self.spec = spec
        # 64 要素の輝度配列を一度だけ確保して再利用することで
        # 毎フレームの GC コストを下げる
        self._levels: list[int] = [0] * self.spec.leds_per_ring

    @classmethod
    @abstractmethod
    def style(cls) -> LedStyle:
        """対応する LedStyle を返す（各サブクラスで実装）"""

    # ----------------- public API -----------------
    @abstractmethod
    def build_levels(self, value: float, style: ValueStyle) -> list[int]:
        """64 要素 (0‒15) の輝度リストを返す"""
        raise NotImplementedError

    # ----------------- helper ---------------------
    def _value_to_norm(self, value: float, style: ValueStyle) -> float:
        """ValueStyle → 0‒1 の正規化値へマップ (小数部保持)"""
        if style == ValueStyle.INFINITE:
            norm = value % 1.0
        else:
            norm = value
        return norm

    def _value_to_pos(self, value: float, style: ValueStyle) -> int:
        """ValueStyle → 0‒63 位置へマップ (整数)"""
        norm = self._value_to_norm(value, style)
        return int(norm * (self.spec.leds_per_ring - 1)) % self.spec.leds_per_ring

    # ----------------- meta ---------------------
    def style_enum(self) -> LedStyle:
        """自身のクラスに対応する LedStyle を返す"""
        return self.__class__.style()


class DotStyle(BaseLedStyle):
    """
    2つのLEDのあいだを線形補間し、リングの端(0と末尾)も連続的に扱うDotStyle。
    """

    @classmethod
    def style(cls) -> LedStyle:
        return LedStyle.DOT

    TAIL_DECAY: float = 0.9

    def __init__(self, max_brightness: int, spec: ArcSpec = ARC_SPEC, tail_decay: float | None = None):
        super().__init__(max_brightness, spec)
        self._leds_per_ring: int = spec.leds_per_ring
        decay_val = self.TAIL_DECAY if tail_decay is None else tail_decay
        self._decay: float = clamp(decay_val, 0.0, 1.0)
        # 浮動小数階調バッファ (残像用)
        self._levels_f: list[float] = [0.0] * self._leds_per_ring

    def build_levels(self, value: float, style: ValueStyle) -> list[int]:
        """
        ドットスタイルの LED レベル配列を生成する。

        残像（テイル）を浮動小数バッファに蓄積し、各フレームで以下を
        1 パスで実行する。

        * 既存残像の減衰
        * 最新ドットの描画（線形補間で 2 LED に分配）
        * 整数レベルへの量子化

        Args:
            value (float): 入力値。``style`` で定義されたスケール
                (例: 0‒1、MIDI 7/14bit など)。
            style (ValueStyle): ``value`` のスケール種別。

        Returns:
            list[int]: 長さ 64 の LED 輝度リスト。各要素は
            ``0‒max_brightness`` の整数。
        """
        n_leds = self._leds_per_ring
        decay = self._decay
        f_levels = self._levels_f
        levels = self._levels

        # 1) 既存残像を減衰しつつ整数バッファへ量子化 (1 パス)
        for i, f in enumerate(f_levels):
            if f > 0.0:
                f *= decay
                f_levels[i] = f
            else:
                f_levels[i] = 0.0
            # 即時量子化して整数バッファを書き戻す
            levels[i] = clamp(int(round(f_levels[i])), 0, self.max_brightness)

        # 2) 現フレームのドット位置を計算
        norm = self._value_to_norm(value, style)
        pos_float = (norm * n_leds) % n_leds
        lower_idx = int(pos_float)  # floor を 1 回で兼用
        upper_idx = (lower_idx + 1) % n_leds
        frac = pos_float - lower_idx

        lower_brightness = (1.0 - frac) * self.max_brightness
        upper_brightness = frac * self.max_brightness

        # 3) 新しい輝度を浮動小数バッファへマージし直ちに整数へ反映
        if lower_brightness > f_levels[lower_idx]:
            f_levels[lower_idx] = lower_brightness
            levels[lower_idx] = clamp(int(round(lower_brightness)), 0, self.max_brightness)

        if upper_brightness > f_levels[upper_idx]:
            f_levels[upper_idx] = upper_brightness
            levels[upper_idx] = clamp(int(round(upper_brightness)), 0, self.max_brightness)
        return levels


class PotentiometerStyle(BaseLedStyle):
    """
    左下(LED40) を 0.0 とし、時計回りにぐるっと回って右下(LED24) が 1.0 になるように帯状に点灯。
    """

    @classmethod
    def style(cls) -> LedStyle:
        return LedStyle.POTENTIOMETER

    def __init__(self, max_brightness: int, spec: ArcSpec = ARC_SPEC):
        """
        インスタンスを初期化し、LED40→LED24 の時計回りアークを
        1 度だけ前計算して保持する。

        Args:
            max_brightness (int): LED の最大輝度 (0‒15)。
            spec (ArcSpec, optional): ハードウェア仕様。既定値は ``ARC_SPEC``。

        Note:
            ``_arc_indices`` と ``_arc_length`` を生成してキャッシュすることで、
            毎フレームのリスト構築コストと ``%`` 演算を削減する。
        """
        super().__init__(max_brightness, spec)
        self._arc_indices: list[int] = self._compute_arc_indices()
        self._arc_length: int = len(self._arc_indices)

    def _compute_arc_indices(self) -> list[int]:
        """
        LED40 (225°) から LED24 (135°) までを時計回りに走査した
        インデックス列を生成する。

        Returns:
            list[int]: LED インデックスのリスト。長さは 49。
        """
        indices: list[int] = []
        i = 40
        while True:
            indices.append(i)
            i = (i + 1) % self.spec.leds_per_ring
            if i == (24 + 1) % self.spec.leds_per_ring:
                break
        return indices

    def build_levels(self, value: float, style: ValueStyle) -> list[int]:
        """
        現在値をもとにポテンショメータ風の帯状グラデーションを生成する。

        Args:
            value (float): 値の正規化前データ。``ValueStyle`` に応じたスケールで与える。
            style (ValueStyle): ``value`` のスケール種別。

        Returns:
            list[int]: 長さ 64 の LED 輝度リスト。起点 (LED40) は輝度 1、
            先端は ``max_brightness``、その間を線形補間したグラデーション。
        """
        levels = self._levels
        levels[:] = [0] * self.spec.leds_per_ring  # いったん全消灯

        # -----------------------------
        # Use the pre‑computed clockwise arc
        # -----------------------------
        arc_indices = self._arc_indices
        arc_length = self._arc_length

        # -----------------------------
        # value を [0,1] に正規化して、arc_indices の途中まで点灯
        # -----------------------------
        norm = self._value_to_norm(value, style)
        norm = max(0.0, min(1.0, norm))  # 0～1 にClamp

        # (A) 先端=max_brightness, 起点(LED40)=1 で線形グラデーション ---------
        pos_float = norm * (arc_length - 1)  # 0.0→48.0
        lower_idx_in_arc = int(math.floor(pos_float))
        frac = pos_float - lower_idx_in_arc  # 0.0～<1.0

        # 先端 LED (lead) は、frac>0 のとき upper、それ以外は lower
        lead_idx_in_arc = lower_idx_in_arc + (1 if frac > 0 else 0)

        # 起点しか点かない (value==0) 場合
        if lead_idx_in_arc == 0:
            levels[arc_indices[0]] = 1
            return levels

        # 起点(1) → 先端(max) へ線形に輝度を一括で計算
        span = lead_idx_in_arc
        brightness_values = np.linspace(1, self.max_brightness, span + 1)
        for idx_in_arc, brightness in enumerate(brightness_values):
            led_i = arc_indices[idx_in_arc]
            levels[led_i] = int(round(brightness))

        return levels


class BipolarStyle(BaseLedStyle):  # TODO バーの先端を最大光度に
    """中央基準で左右に伸びる表示"""

    @classmethod
    def style(cls) -> LedStyle:
        return LedStyle.BIPOLAR

    # -------------------- 定数 --------------------
    CENTER_IDX = 0  # 真上
    RIGHT_DOWN_IDX = 21  # 120°
    LEFT_DOWN_IDX = 43  # 240°
    MAX_SPAN = 21  # 0→21 で約 120°

    def build_levels(self, value: float, style: ValueStyle) -> list[int]:
        """
        バイポーラ表示を生成する。

        真上 (LED0) をセンターとして、負方向は反時計回りに左下 (LED43)
        まで、正方向は時計回りに右下 (LED21) までの範囲で帯を伸ばす。
        センター LED は最大輝度、帯部分は dim 輝度で描画する。

        Args:
            value (float): ring_stateのcurrent_value。
            style (ValueStyle): ``value`` のスケール種別。

        Returns:
            list[int]: 64 要素の輝度リスト。
        """
        n_leds = self.spec.leds_per_ring
        levels = self._levels
        levels[:] = [0] * n_leds

        # --- 基本点灯 ----------------------------------------------------
        dim = max(1, self.max_brightness // 4)
        levels[self.CENTER_IDX] = self.max_brightness
        levels[self.LEFT_DOWN_IDX] = dim
        levels[self.RIGHT_DOWN_IDX] = dim

        # --- 入力値を -0.5‒+0.5 に正規化 ---------------------------------
        centered_value = self._value_to_norm(value, style) - 0.5
        centered_value = max(-0.5, min(0.5, centered_value))
        if centered_value == 0.0:
            return levels

        # --- 帯を描画 ----------------------------------------------------
        span_steps = int(round(abs(centered_value) * self.MAX_SPAN * 2))  # 0‒24
        if span_steps == 0:
            return levels

        step_sign = 1 if centered_value > 0 else -1
        for step in range(1, span_steps + 1):
            idx = (self.CENTER_IDX + step_sign * step) % n_leds
            levels[idx] = dim

        return levels


class PerlinLedStyle(BaseLedStyle):
    """Perlin ノイズ空間を使って LED を揺らす表示"""

    @classmethod
    def style(cls) -> LedStyle:
        return LedStyle.PERLIN

    # ---------------------- パラメータ定数 ----------------------
    PHI = (1 + math.sqrt(5)) / 2  # 黄金比
    MINIMUM_NOISE_RADIUS = PHI / 2.0
    NOISE_RADIUS_SCALE = 5.0
    MOVE_SPEED = 0.1
    NOISE_POSITION_INCREMENT = 0.01
    NOISE_POSITION_Y_SCALE = 0.3
    BRIGHTNESS_SCALE = 2.0
    BRIGHTNESS_OFFSET = 0.5

    def __init__(self, max_brightness: int = 15) -> None:
        super().__init__(max_brightness)
        self.noise_position = 0.0
        self.noise_seed = random.randint(0, 2**8)
        self.previous_norm = 0.0
        self._cos_table = [math.cos(math.tau * i / self.spec.leds_per_ring) for i in range(self.spec.leds_per_ring)]
        self._sin_table = [math.sin(math.tau * i / self.spec.leds_per_ring) for i in range(self.spec.leds_per_ring)]

    # --------------------- private helper ---------------------
    def _update_noise_position(self, norm: float) -> None:
        """value 変化に応じてノイズ空間の走査位置を進める"""
        if norm != self.previous_norm:  # value=0 のときは進めない
            self.noise_position += norm * self.MOVE_SPEED + self.NOISE_POSITION_INCREMENT
        self.previous_norm = norm

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
        norm = self._value_to_norm(value, style)
        radius = self.MINIMUM_NOISE_RADIUS + norm * self.NOISE_RADIUS_SCALE
        self._update_noise_position(norm)

        # LED ごとに輝度計算 (③ coords 計算をインライン化 + テーブル参照)
        pos = self.noise_position
        y_scale = self.NOISE_POSITION_Y_SCALE * pos
        for i in range(self.spec.leds_per_ring):
            nx = radius * self._cos_table[i] + pos
            ny = radius * self._sin_table[i] + y_scale
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


def get_led_instance(style: LedStyle, max_brightness: int = 15) -> BaseLedStyle:
    cls = LED_STYLE_MAP.get(style)
    if cls is None:
        LOGGER.warning("Unknown LedStyle %s – fallback to DOT", style)
        cls = DotStyle
    return cls(max_brightness)
