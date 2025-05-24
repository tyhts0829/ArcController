import logging
import math
import random
from abc import ABC, abstractmethod

import noise

from src.enums.enums import LfoStyle
from src.model.model import RingState

LOGGER = logging.getLogger(__name__)


class BaseLfoStyle(ABC):
    """
    リング値を経時変化させるアルゴリズムの共通インターフェース
    各 Strategy は 純粋に計算だけ 行い、副作用（LED 更新・MIDI 送信など）は持たせない
    速度 (speed) やゲイン (amplitude) は RingState 側に保持 させ、ノブ回転で即時変更できるようにする
    """

    @classmethod
    @abstractmethod
    def style(cls) -> LfoStyle:
        """対応する LfoStyle を返す（各サブクラスで実装）"""

    # ----------------- public API -----------------
    @abstractmethod
    def update(self, ring_state: RingState, dt: float) -> float:
        raise NotImplementedError

    # ----------------- meta ---------------------
    def style_enum(self) -> LfoStyle:
        """自身のクラスに対応する LfoStyle を返す"""
        return self.__class__.style()


class StaticLfoStyle(BaseLfoStyle):
    """LFOを使わないときに指定するクラス"""

    @classmethod
    def style(cls) -> LfoStyle:
        return LfoStyle.STATIC

    def update(self, ring_state: RingState, dt: float) -> float:  # 何もしない
        return ring_state.value


class SineLfoStyle(BaseLfoStyle):
    """正弦波を返すクラス"""

    @classmethod
    def style(cls) -> LfoStyle:
        return LfoStyle.SINE

    def update(self, ring_state: RingState, dt: float) -> float:
        ring_state.lfo_phase = (ring_state.lfo_phase + ring_state.lfo_frequency * dt) % 1.0
        return ring_state.lfo_amplitude * math.sin(2.0 * math.pi * ring_state.lfo_phase)


class SawLfoStyle(BaseLfoStyle):
    """鋸波を返すクラス"""

    @classmethod
    def style(cls) -> LfoStyle:
        return LfoStyle.SAW

    def update(self, ring_state: RingState, dt: float) -> float:
        ring_state.lfo_phase = (ring_state.lfo_phase + ring_state.lfo_frequency * dt) % 1.0
        return ring_state.lfo_amplitude * (2.0 * ring_state.lfo_phase - 1.0)


class SquareLfoStyle(BaseLfoStyle):
    """矩形波を返すクラス"""

    @classmethod
    def style(cls) -> LfoStyle:
        return LfoStyle.SQUARE

    def update(self, ring_state: RingState, dt: float) -> float:
        ring_state.lfo_phase = (ring_state.lfo_phase + ring_state.lfo_frequency * dt) % 1.0
        return ring_state.lfo_amplitude if ring_state.lfo_phase < 0.5 else -ring_state.lfo_amplitude


class TriangleLfoStyle(BaseLfoStyle):
    """三角波を返すクラス"""

    @classmethod
    def style(cls) -> LfoStyle:
        return LfoStyle.TRIANGLE

    def update(self, ring_state: RingState, dt: float) -> float:
        ring_state.lfo_phase = (ring_state.lfo_phase + ring_state.lfo_frequency * dt) % 1.0
        tri = 4.0 * abs(ring_state.lfo_phase - 0.5) - 1.0  # -1..1
        return ring_state.lfo_amplitude * tri


class PerlinLfoStyle(BaseLfoStyle):
    """Perlin noiseを返すクラス"""

    @classmethod
    def style(cls) -> LfoStyle:
        return LfoStyle.PERLIN

    def update(self, ring_state: RingState, dt: float) -> float:
        ring_state.lfo_phase += ring_state.lfo_frequency * dt
        val = noise.pnoise1(ring_state.lfo_phase, base=ring_state.cc_number * 10)  # -1.0〜1.0の範囲
        val = val + 1  # 0.0〜2.0にシフト
        return ring_state.lfo_amplitude * val  # 振幅が0 < 振幅 < 1.0 になるように補正


class RandomEaseLfoStyle(BaseLfoStyle):
    """一定間隔ごとにランダムな目標値を生成し、イージングで滑らかに追従するLFO。

    特徴:
    - lfo_frequency が高いほど、目標値の更新頻度が高くなります
    - 目標値への追従はイージング関数により滑らかに行われます
    - 各CC番号ごとに独立した状態を管理します

    設定値:
    - MIN_INTERVAL: 最短更新間隔（lfo_frequency = 1.0 時）
    - MAX_INTERVAL: 最長更新間隔（lfo_frequency = 0.0 時）
    - EASING_COEFFICIENT: イージングの強度（0に近いほど緩やか、1で即座に変化）
    """

    # 定数定義
    MIN_INTERVAL: float = 0.2  # 秒
    MAX_INTERVAL: float = 2.0  # 秒
    EASING_COEFFICIENT: float = 0.1  # 0 < coefficient ≤ 1
    OUTPUT_SCALE: float = 2.0  # 出力値のスケール係数

    # 各CC番号の状態を管理するテーブル
    _states: dict[int, dict[str, float]] = {}

    @classmethod
    def style(cls) -> LfoStyle:
        return LfoStyle.RANDOM_EASE

    def update(self, ring_state: RingState, dt: float) -> float:
        """LFO値を更新して返します。

        Args:
            ring_state: リングの現在状態
            dt: 前回更新からの経過時間（秒）

        Returns:
            更新されたLFO値
        """
        # 早期リターン: LFOが無効な場合
        if self._should_return_early(ring_state):
            return self._get_early_return_value(ring_state)

        # 状態の取得または初期化
        state = self._get_or_initialize_state(ring_state.cc_number)

        # 更新間隔の計算
        update_interval = self._calculate_update_interval(ring_state.lfo_frequency)

        # 目標値の更新判定と実行
        self._update_target_if_needed(state, dt, update_interval)

        # イージングによる値の更新
        self._apply_easing(state)

        # 最終出力値の計算
        return self._calculate_output(ring_state, state)

    def _should_return_early(self, ring_state: RingState) -> bool:
        """早期リターンが必要かどうかを判定します。"""
        return ring_state.lfo_frequency == 0.0 or ring_state.lfo_amplitude == 0.0

    def _get_early_return_value(self, ring_state: RingState) -> float:
        """早期リターン時の戻り値を取得します。"""
        if ring_state.lfo_frequency == 0.0:
            return ring_state.value
        return 0.0  # lfo_amplitude == 0.0 の場合

    def _get_or_initialize_state(self, cc_number: int) -> dict[str, float]:
        """指定されたCC番号の状態を取得、または初期化します。"""
        state = self._states.get(cc_number)
        if state is None:
            initial_target = random.random()
            state = {"target": initial_target, "value": initial_target, "timer": 0.0}
            self._states[cc_number] = state
        return state

    def _calculate_update_interval(self, lfo_frequency: float) -> float:
        """LFO周波数に基づいて更新間隔を計算します。"""
        # 周波数を0.0-1.0の範囲にクランプ
        clamped_frequency = max(0.0, min(1.0, lfo_frequency))

        # 線形補間: frequency=0 → MAX_INTERVAL, frequency=1 → MIN_INTERVAL
        return self.MAX_INTERVAL + (self.MIN_INTERVAL - self.MAX_INTERVAL) * clamped_frequency

    def _update_target_if_needed(self, state: dict[str, float], dt: float, interval: float) -> None:
        """必要に応じて目標値を更新します。"""
        state["timer"] += dt

        if state["timer"] >= interval:
            # タイマーをリセット（余剰時間を保持）
            state["timer"] %= interval
            # 新しい目標値を生成
            state["target"] = random.random()

    def _apply_easing(self, state: dict[str, float]) -> None:
        """イージング関数を適用して現在値を更新します。"""
        difference = state["target"] - state["value"]
        state["value"] += difference * self.EASING_COEFFICIENT

    def _calculate_output(self, ring_state: RingState, state: dict[str, float]) -> float:
        """最終的な出力値を計算します。"""
        return ring_state.lfo_amplitude * state["value"] * self.OUTPUT_SCALE


# -----------------------------------------------------------------------------
# Factory
# -----------------------------------------------------------------------------
LFO_STYLE_MAP = {
    LfoStyle.STATIC: StaticLfoStyle,
    LfoStyle.SINE: SineLfoStyle,
    LfoStyle.SAW: SawLfoStyle,
    LfoStyle.SQUARE: SquareLfoStyle,
    LfoStyle.TRIANGLE: TriangleLfoStyle,
    LfoStyle.PERLIN: PerlinLfoStyle,
    LfoStyle.RANDOM_EASE: RandomEaseLfoStyle,
}


def get_lfo_instance(style: LfoStyle) -> BaseLfoStyle:
    cls = LFO_STYLE_MAP.get(style)
    if cls is None:
        LOGGER.warning("Unknown LfoStyle %s – fallback to STATIC", style)
        cls = StaticLfoStyle
    return cls()
