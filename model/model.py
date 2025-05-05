import logging
from dataclasses import dataclass, field
from typing import Any

from controller.lfo_strategy import LFO_FACTORIES, LfoStrategy
from enums.enums import LedStyle, LfoStyle, ValueStyle
from util.util import clamp, fmt

LOGGER = logging.getLogger("RingState")


@dataclass
class RingState:
    current_value: float = 0.0
    cc_number: int = 0  # レイヤーごとに割り当てる
    value_style: ValueStyle = ValueStyle.LINEAR
    led_style: LedStyle = LedStyle.DOT
    lfo_style: LfoStyle = LfoStyle.PERLIN
    lfo_strategy: LfoStrategy = field(init=False, default=None)
    _lfo_frequency: float = 0.1
    lfo_amplitude: float = 0.5  # 固定
    lfo_phase: float = 0.0  # 固定

    def __post_init__(self):
        self.set_lfo(self.lfo_style)

    def set_lfo(self, lfo_style: LfoStyle):
        self.lfo_style = lfo_style
        self.lfo_strategy = LFO_FACTORIES[lfo_style]()  # DI

    # 変数を書き換えたときにログ出力するフック
    def __setattr__(self, name: str, value: Any) -> None:
        old = self.__dict__.get(name, None)
        super().__setattr__(name, value)
        if old != value:
            LOGGER.info("%s: %s -> %s", name, fmt(old), fmt(value))

    @property
    def lfo_frequency(self) -> float:
        return self._lfo_frequency

    @lfo_frequency.setter
    def lfo_frequency(self, value: float) -> None:
        MIN = 0.0
        MAX = 10.0
        self._lfo_frequency = clamp(value, MIN, MAX)


@dataclass
class LayerState:
    rings: list[RingState]


@dataclass
class Model:
    rings: list[RingState] = field(default_factory=lambda: [RingState() for _ in range(4)])

    def __getitem__(self, index: int) -> RingState:
        return self.rings[index]
