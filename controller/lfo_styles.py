import logging
import math
import random
from abc import ABC, abstractmethod
from functools import cached_property

import noise

from enums.enums import LfoStyle
from model.model import RingState

LOGGER = logging.getLogger(__name__)


class BaseLfoStyle(ABC):
    """
    リング値を経時変化させるアルゴリズムの共通インターフェース
    各 Strategy は 純粋に計算だけ 行い、副作用（LED 更新・MIDI 送信など）は持たせない
    速度 (speed) やゲイン (amplitude) は RingState 側に保持 させ、ノブ回転で即時変更できるようにする
    """

    # ----------------- public API -----------------
    @abstractmethod
    def update(self, ring_state: RingState, dt: float) -> float:
        raise NotImplementedError

    # ----------------- meta ---------------------
    @cached_property
    def style_enum(self) -> LfoStyle | str:
        """
        自身のクラスに対応する LfoStyle を返す
        未登録の場合はクラス名文字列を返す
        """
        return LFO_CLASS_TO_STYLE_ENUM.get(self.__class__, self.__class__.__name__)


class StaticLfoStyle(BaseLfoStyle):
    """LFOを使わないときに指定するクラス"""

    def update(self, ring_state: RingState, dt: float) -> float:  # 何もしない
        return ring_state.current_value


class RandomLfoStyle(BaseLfoStyle):
    def update(self, ring_state: RingState, dt: float) -> float:
        jitter = (random.random() - 0.5) * ring_state.lfo_frequency * dt
        return jitter


class SineLfoStyle(BaseLfoStyle):
    """正弦波を返すクラス"""

    def update(self, ring_state: RingState, dt: float) -> float:
        ring_state.lfo_phase = (ring_state.lfo_phase + ring_state.lfo_frequency * dt) % 1.0
        return ring_state.lfo_amplitude * math.sin(2.0 * math.pi * ring_state.lfo_phase)


class SawLfoStyle(BaseLfoStyle):
    """鋸波を返すクラス"""

    def update(self, ring_state: RingState, dt: float) -> float:
        ring_state.lfo_phase = (ring_state.lfo_phase + ring_state.lfo_frequency * dt) % 1.0
        return ring_state.lfo_amplitude * (2.0 * ring_state.lfo_phase - 1.0)


class SquareLfoStyle(BaseLfoStyle):
    """矩形波を返すクラス"""

    def update(self, ring_state: RingState, dt: float) -> float:
        ring_state.lfo_phase = (ring_state.lfo_phase + ring_state.lfo_frequency * dt) % 1.0
        return ring_state.lfo_amplitude if ring_state.lfo_phase < 0.5 else -ring_state.lfo_amplitude


class TriangleLfoStyle(BaseLfoStyle):
    """三角波を返すクラス"""

    def update(self, ring_state: RingState, dt: float) -> float:
        ring_state.lfo_phase = (ring_state.lfo_phase + ring_state.lfo_frequency * dt) % 1.0
        tri = 4.0 * abs(ring_state.lfo_phase - 0.5) - 1.0  # -1..1
        return ring_state.lfo_amplitude * tri


class PerlinLfoStyle(BaseLfoStyle):
    """Perlin noiseを返すクラス"""

    def update(self, ring_state: RingState, dt: float) -> float:
        ring_state.lfo_phase += ring_state.lfo_frequency * dt
        val = noise.pnoise1(ring_state.lfo_phase, base=ring_state.cc_number * 10)
        return ring_state.lfo_amplitude * val


# -----------------------------------------------------------------------------
# Factory
# -----------------------------------------------------------------------------
LFO_STYLE_MAP = {
    LfoStyle.STATIC: StaticLfoStyle,
    LfoStyle.RANDOM: RandomLfoStyle,
    LfoStyle.SINE: SineLfoStyle,
    LfoStyle.SAW: SawLfoStyle,
    LfoStyle.SQUARE: SquareLfoStyle,
    LfoStyle.TRIANGLE: TriangleLfoStyle,
    LfoStyle.PERLIN: PerlinLfoStyle,
}
# 逆引き: クラス → LfoStyle
LFO_CLASS_TO_STYLE_ENUM: dict[type[BaseLfoStyle], LfoStyle] = {v: k for k, v in LFO_STYLE_MAP.items()}


def get_lfo_instance(style: LfoStyle) -> BaseLfoStyle:
    cls = LFO_STYLE_MAP.get(style)
    if cls is None:
        LOGGER.warning("Unknown LfoStyle %s – fallback to STATIC", style)
        cls = StaticLfoStyle
    return cls()
