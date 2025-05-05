import math
import random
from abc import ABC, abstractmethod

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
    def __init__(self):
        self.t = 0.0

    def update(self, ring_state, dt):
        self.t += dt
        return ring_state.lfo_amplitude * math.sin(2 * math.pi * ring_state.lfo_frequency * self.t)


LFO_FACTORIES = {
    LfoStyle.STATIC: lambda: StaticLfo(),
    LfoStyle.RANDOM: lambda: RandomLfo(),
    LfoStyle.SINE: lambda: SineLfo(),
}
