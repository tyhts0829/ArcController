import logging
from dataclasses import dataclass, field
from typing import Any

from enums.enums import Behavior, LedStyle, ValueStyle

LOGGER = logging.getLogger("RingState")


@dataclass
class RingState:
    current_value: float = 0.0  # ADD: Store last calculated value
    cc_number: int = 0  # レイヤーごとに割り当てる CC 番号
    led_style: str = LedStyle.DOT
    behavior: str = Behavior.STATIC
    value_style: str = ValueStyle.LINEAR

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
