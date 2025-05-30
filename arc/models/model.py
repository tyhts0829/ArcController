from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Iterator, List

from arc.enums.enums import LedStyle, LfoStyle, ValueStyle
from arc.utils.hardware_spec import ARC_SPEC
from arc.utils.util import clamp, fmt

LOGGER = logging.getLogger(__name__)


@dataclass
class Model:
    """アプリ全体の状態を管理するルートクラス。

    Attributes:
        num_layers (int): レイヤー数。
        layers (List[LayerState]): 各レイヤーの状態リスト。
        active_layer_idx (int): 現在アクティブなレイヤー番号。
    """

    num_layers: int = 4
    layers: List["LayerState"] = field(init=False)
    active_layer_idx: int = 0  # 現在の編集対象レイヤー

    def __post_init__(self) -> None:
        # num_layers に基づいて layers を生成
        self.layers = [LayerState(name=f"L{i}") for i in range(self.num_layers)]

    @classmethod
    def from_config(cls, cfg) -> "Model":
        try:
            num_layers = cfg.model.num_layers
        except AttributeError:
            num_layers = 4
            LOGGER.warning("cfg.model.num_layers not found – fallback to %d layers", num_layers)

        model = cls(num_layers=num_layers)

        # プリセットと CC 番号を各リングに適用
        default_preset = cfg.presets[0]
        for layer_idx, layer in enumerate(model.layers):
            for ring_idx, ring in enumerate(layer):
                # cc_number を 1‒16 で割り当てる (4 レイヤー × 4 リング)
                ring.cc_number = layer_idx * ARC_SPEC.rings_per_device + ring_idx + 1
                ring.set_presets(cfg.presets)
                ring.apply_preset(default_preset)
        return model

    @property
    def active_layer(self) -> "LayerState":
        return self.layers[self.active_layer_idx]

    def cycle_layer(self, step: int = 1) -> None:
        """active_layer_idx を循環的に進める。"""
        LOGGER.info("Layer %d -> %d", self.active_layer_idx, (self.active_layer_idx + step) % len(self.layers))
        self.active_layer_idx = (self.active_layer_idx + step) % len(self.layers)

    def __getitem__(self, ring_idx: int) -> "RingState":
        return self.active_layer[ring_idx]

    def __iter__(self) -> Iterator["LayerState"]:
        return iter(self.layers)


@dataclass
class LayerState:
    """1 レイヤー分のリング集合を表すデータクラス。"""

    rings: List[RingState] = field(default_factory=lambda: [RingState() for _ in range(ARC_SPEC.rings_per_device)])
    name: str = "Layer"  # 任意：UI 表示用

    def __getitem__(self, ring_idx: int) -> RingState:
        return self.rings[ring_idx]

    def __iter__(self) -> Iterator[RingState]:
        return iter(self.rings)


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
        value_gain (float): ringΔに対するvalueの増分
        lfo_freq_gain (float): ringΔに対するlfo周波数の増分
    """

    value: float = 0.0
    cc_number: int = 0  # レイヤーごとに割り当てる
    value_style: ValueStyle = ValueStyle.LINEAR
    led_style: LedStyle = LedStyle.PERLIN
    lfo_style: LfoStyle = LfoStyle.PERLIN
    lfo_frequency: float = 0.5  # 0.0‒1.0 の範囲で LFO 周波数を表現
    lfo_amplitude: float = 0.5  # 固定。外部アプリケーションでスケールすること前提のため。
    lfo_phase: float = 0.0
    preset_index: int = 0  # 現在のプリセット番号
    _presets: List[dict] = field(default_factory=list, repr=False)
    value_gain: float = 0.001
    lfo_freq_gain: float = 0.0005

    # 変数を書き換えたときにログ出力するフック。TODO: いずれやめる
    def __setattr__(self, name: str, value: Any) -> None:
        old = self.__dict__.get(name, None)
        super().__setattr__(name, value)
        if old != value:
            LOGGER.debug("%s: %s -> %s", name, fmt(old), fmt(value))

    def apply_preset(self, preset: dict) -> None:
        """プリセットから各種スタイルを更新し、BIPOLAR なら current_value を 0.5 に補正する。

        Args:
            preset (dict): プリセット定義。
        """
        self.value_style = ValueStyle(preset["value_style"])
        self.led_style = LedStyle(preset["led_style"])
        self.lfo_style = LfoStyle(preset["lfo_style"])
        # ValueStyle が BIPOLAR に切り替わった場合、論理的な中央値をセットする
        if self.value_style == ValueStyle.BIPOLAR or self.led_style == LedStyle.BIPOLAR:
            self.value = 0.5

    def apply_delta(self, delta: int) -> None:
        """リングの現在値をスタイルに応じて更新する。

        Args:
            delta (float): 入力エンコーダの増分。
        """
        style = self.value_style
        new_val = self.value + delta * self.value_gain

        # --- スタイル別の丸め・制限 -------------------------------
        if style != ValueStyle.INFINITE:  # 無限値は制限しない
            new_val = clamp(new_val, 0.0, 1.0)

        self.value = new_val

    def apply_lfo_delta(self, delta: float) -> None:
        """LFO 周波数を 0.0‒1.0 範囲で更新する。

        Args:
            delta (float): 入力エンコーダの増分。
        """
        new_val = self.lfo_frequency + delta * self.lfo_freq_gain
        self.lfo_frequency = clamp(new_val, 0.0, 1.0)

    def cycle_preset(self, step: int = 1) -> None:
        """プリセットインデックスを循環的に進める。"""
        """プリセットインデックスを循環的に進め、対応するプリセットを即時適用する。"""
        if not self._presets:
            LOGGER.warning("Preset list is empty – cannot cycle preset.")
            return
        LOGGER.info("Preset %d -> %d", self.preset_index, (self.preset_index + step) % len(self._presets))
        self.preset_index = (self.preset_index + step) % len(self._presets)
        self.apply_preset(self._presets[self.preset_index])

    def set_presets(self, presets: List[dict]) -> None:
        """リングで使用可能なプリセットリストを保存し、総数を更新する。"""
        self._presets = presets
