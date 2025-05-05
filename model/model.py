import logging
from dataclasses import dataclass, field
from typing import Any

from controller.lfo_strategy import LFO_FACTORIES, LfoStrategy
from enums.enums import LedStyle, LfoStyle, ValueStyle

LOGGER = logging.getLogger("RingState")


@dataclass
class RingState:
    current_value: float = 0.0
    cc_number: int = 0  # レイヤーごとに割り当てる
    value_style: str = ValueStyle.LINEAR
    led_style: str = LedStyle.DOT
    lfo_style: str = LfoStyle.SINE
    lfo_frequency: float = 0.1
    lfo_amplitude: float = 0.5  # 固定
    lfo_phase: float = 0.0  # 固定
    lfo_strategy: LfoStrategy = field(init=False, default=None)

    def __post_init__(self):
        self.set_lfo(self.lfo_style)

    def set_lfo(self, lfo_style: str):
        self.lfo_style = lfo_style
        self.lfo_strategy = LFO_FACTORIES[lfo_style]()  # DI

    # 変数を書き換えたときにログ出力するフック
    def __setattr__(self, name: str, value: Any) -> None:
        old = self.__dict__.get(name, None)
        super().__setattr__(name, value)
        if old != value:
            LOGGER.info("%s: %s -> %s", name, self._fmt(old), self._fmt(value))
        super().__setattr__(name, value)

    # --- helper --------------------------------------------------------
    @staticmethod
    def _fmt(v: Any) -> str:
        """Floats → 3桁小数、その他はそのまま文字列化"""
        return f"{v:.3f}" if isinstance(v, float) else str(v)


@dataclass
class LayerState:
    rings: list[RingState]


@dataclass
class Model:
    rings: list[RingState] = field(default_factory=lambda: [RingState() for _ in range(4)])

    def __getitem__(self, index: int) -> RingState:
        return self.rings[index]
