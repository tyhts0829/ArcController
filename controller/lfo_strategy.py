import math
import random
from abc import ABC, abstractmethod

import noise

from enums.enums import LfoStyle


class LfoStrategy(ABC):
    """
    リング値を経時変化させるアルゴリズムの共通インターフェース
    各 Strategy は 純粋に計算だけ 行い、副作用（LED 更新・MIDI 送信など）は持たせない
    速度 (speed) やゲイン (amplitude) は RingState 側に保持 させ、ノブ回転で即時変更できるようにする
    """

    @abstractmethod
    def update(self, ring_state, dt: float) -> float:
        raise NotImplementedError


class StaticLfo(LfoStrategy):
    def update(self, ring_state, dt):  # 何もしない
        return ring_state.current_value


class RandomLfo(LfoStrategy):
    def update(self, ring_state, dt):
        jitter = (random.random() - 0.5) * ring_state.lfo_frequency * dt
        return jitter


class SineLfo(LfoStrategy):
    def update(self, ring_state, dt):
        ring_state.lfo_phase = (ring_state.lfo_phase + ring_state.lfo_frequency * dt) % 1.0
        return ring_state.lfo_amplitude * math.sin(2.0 * math.pi * ring_state.lfo_phase)


class SawLfo(LfoStrategy):
    def update(self, ring_state, dt):
        ring_state.lfo_phase = (ring_state.lfo_phase + ring_state.lfo_frequency * dt) % 1.0
        return ring_state.lfo_amplitude * (2.0 * ring_state.lfo_phase - 1.0)


class SquareLfo(LfoStrategy):
    def update(self, ring_state, dt):
        ring_state.lfo_phase = (ring_state.lfo_phase + ring_state.lfo_frequency * dt) % 1.0
        return ring_state.lfo_amplitude if ring_state.lfo_phase < 0.5 else -ring_state.lfo_amplitude


class TriangleLfo(LfoStrategy):
    def update(self, ring_state, dt):
        ring_state.lfo_phase = (ring_state.lfo_phase + ring_state.lfo_frequency * dt) % 1.0
        tri = 4.0 * abs(ring_state.lfo_phase - 0.5) - 1.0  # -1..1
        return ring_state.lfo_amplitude * tri


class PerlinLfo(LfoStrategy):
    def update(self, ring_state, dt):
        # x を積分して連続性を確保
        ring_state.lfo_phase += ring_state.lfo_frequency * dt
        val = noise.pnoise1(ring_state.lfo_phase)
        return ring_state.lfo_amplitude * val


LFO_FACTORIES = {
    LfoStyle.STATIC: lambda: StaticLfo(),
    LfoStyle.RANDOM: lambda: RandomLfo(),
    LfoStyle.SINE: lambda: SineLfo(),
    LfoStyle.SAW: lambda: SawLfo(),
    LfoStyle.SQUARE: lambda: SquareLfo(),
    LfoStyle.TRIANGLE: lambda: TriangleLfo(),
    LfoStyle.PERLIN: lambda: PerlinLfo(),
}
