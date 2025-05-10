"""
model.model
-----------

Arc アプリケーションの状態を保持するデータクラス群。
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Iterator

from enums.enums import LedStyle, LfoStyle, ValueStyle
from util.util import fmt

LOGGER = logging.getLogger(__name__)


@dataclass
class RingState:
    """
    1 つのリングに関するランタイム状態を保持するデータクラス。

    Attributes:
        current_value (float): 現在値 (0.0‒1.0 など)。
        cc_number (int): 対応する MIDI CC 番号。
        value_style (ValueStyle): 値の表現スタイル。
        led_style (LedStyle): LED 表示スタイル。
        lfo_style (LfoStyle): LFO 生成スタイル。
        lfo_frequency (float): LFO 周波数 (0.0‒1.0)。
        lfo_amplitude (float): LFO 振幅。
        lfo_phase (float): LFO 位相 (0.0‒1.0)。
        preset_index (int): 適用中プリセットのインデックス。
    """

    current_value: float = 0.0
    cc_number: int = 0  # レイヤーごとに割り当てる
    value_style: ValueStyle = ValueStyle.LINEAR
    led_style: LedStyle = LedStyle.PERLIN
    lfo_style: LfoStyle = LfoStyle.PERLIN
    lfo_frequency: float = 0.1
    lfo_amplitude: float = 0.5  # 固定。外部アプリケーションでスケールすること前提のため。
    lfo_phase: float = 0.0
    preset_index: int = 0  # 現在のプリセット番号

    # 変数を書き換えたときにログ出力するフック
    def __setattr__(self, name: str, value: Any) -> None:
        old = self.__dict__.get(name, None)
        super().__setattr__(name, value)
        if old != value:
            LOGGER.debug("%s: %s -> %s", name, fmt(old), fmt(value))

    def apply_preset(self, preset: dict) -> None:
        """プリセット dict から value_style / led_style / lfo_style を更新する。

        Args:
            preset (dict): プリセット定義。
        """
        self.value_style = ValueStyle(preset["value_style"])
        self.led_style = LedStyle(preset["led_style"])
        self.lfo_style = LfoStyle(preset["lfo_style"])


@dataclass
class LayerState:
    """
    1 レイヤー分のリング集合を表すデータクラス。

    Attributes:
        rings (list[RingState]): 4 つのリング状態を保持するリスト。
    """

    rings: list[RingState]


@dataclass
class Model:
    """
    アプリ全体の状態を管理するトップレベルデータクラス。

    Attributes:
        rings (list[RingState]): 4 つのリング状態を保持するリスト。
    """

    rings: list[RingState] = field(default_factory=lambda: [RingState() for _ in range(4)])

    def __getitem__(self, ring_idx: int) -> RingState:
        """list 風インデックスアクセスを提供する。

        Args:
            ring_idx (int): リングのインデックス (0‑3)。

        Returns:
            RingState: 対象リングの状態。
        """
        return self.rings[ring_idx]

    def __iter__(self) -> Iterator[RingState]:
        """イテレータプロトコルを実装して `for ring in model` を可能にする。

        Returns:
            Iterator[RingState]: リング状態のイテレータ。
        """
        return iter(self.rings)
