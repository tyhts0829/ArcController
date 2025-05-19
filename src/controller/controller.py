"""
controller.controller
---------------------

monome Arc デバイスからの入力イベントを Model / LED / LFO へ橋渡しする
コントローラクラスを定義するモジュール。
"""

import asyncio
import logging
import typing

# from enum import Enum  # no longer needed
from typing import Optional

import monome
import transitions
from transitions import EventData, Machine, State

from src.enums.enums import Mode
from src.model.model import Model
from src.modes.base_mode import BaseMode
from src.modes.disconnect_mode import DisconnectMode
from src.modes.layer_select_mode import LayerSelectMode
from src.modes.preset_select_mode import PresetSelectMode
from src.modes.ready_mode import ReadyMode
from src.modes.value_send_mode import ValueSendMode

LOGGER = logging.getLogger(__name__)


STATES = [
    State(name=Mode.READY_MODE),
    State(name=Mode.PRESET_SELECT_MODE, on_enter="_on_enter_preset_select", on_exit="_on_exit_preset_select"),
    State(name=Mode.LAYER_SELECT_MODE, on_enter="_on_enter_layer_select", on_exit="_on_exit_layer_select"),
    State(name=Mode.VALUE_SEND_MODE),
    State(name=Mode.DISCONNECT_MODE),
]
TRANSITIONS = [
    {"trigger": "press", "source": "*", "dest": Mode.LAYER_SELECT_MODE},
    {"trigger": "long_press", "source": Mode.LAYER_SELECT_MODE, "dest": Mode.PRESET_SELECT_MODE},
    {"trigger": "release", "source": "*", "dest": Mode.VALUE_SEND_MODE},
    {"trigger": "_on_arc_ready", "source": "*", "dest": Mode.VALUE_SEND_MODE},
    {"trigger": "_on_arc_disconnect", "source": "*", "dest": Mode.DISCONNECT_MODE},
]


class ArcController(monome.ArcApp):
    """
    モノーム Arc デバイスからの入力を処理し、状態遷移や LED レンダリング、
    LFO 生成などの各コンポーネントへ橋渡しを行うコントローラクラス。

    Attributes:
        machine (transitions.Machine): 入力イベントに応じた状態遷移を管理するステートマシン。
        _long_press_timer (Optional[asyncio.TimerHandle]): 長押し判定用タイマー。
        _is_pressed (bool): 現在の押下状態フラグ。
    """

    def __init__(
        self,
        model: Model,
        mode_mapping: dict[Mode, BaseMode],
    ) -> None:
        super().__init__()
        self.model = model
        self.state: Optional[Mode] = None
        self._modes: dict[Mode, BaseMode] = mode_mapping
        self.ready_mode = typing.cast(ReadyMode, self._modes[Mode.READY_MODE])
        self.value_send_mode = typing.cast(ValueSendMode, self._modes[Mode.VALUE_SEND_MODE])
        self.layer_select_mode = typing.cast(LayerSelectMode, self._modes[Mode.LAYER_SELECT_MODE])
        self.preset_select_mode = typing.cast(PresetSelectMode, self._modes[Mode.PRESET_SELECT_MODE])
        self.disconnect_mode = typing.cast(DisconnectMode, self._modes[Mode.DISCONNECT_MODE])
        self.machine: Machine = transitions.Machine(
            model=self,
            states=STATES,
            transitions=TRANSITIONS,
            initial=Mode.VALUE_SEND_MODE,
            send_event=True,
            auto_transitions=False,
        )
        self._long_press_timer: Optional[asyncio.TimerHandle] = None
        self._is_pressed: bool = False

    # ---------------------------------
    # public methods
    # ---------------------------------

    def on_arc_key(self, x: int, pressed: bool) -> None:
        """
        Arc デバイスのキーイベントを受け取り、押下／離上に応じて処理を振り分ける。

        Args:
            x (int): キー番号（本クラスでは使用しないが、コールバック仕様に合わせて受け取る）。
            pressed (bool): 押下時 True、離上時 False。
        """
        if pressed:
            self._on_key_pressed()
        else:
            self._on_key_released()

    def on_arc_delta(self, ring_idx: int, delta: int) -> None:
        """
        Arc デバイスのダイヤルイベントを受け取り、現在のモードに委譲する。

        Args:
            ring_idx (int): ダイヤル番号。
            delta (int): ダイヤルの変化量。
        """
        state = self.state
        if state is None:
            LOGGER.error("State is None: cannot dispatch on_arc_delta")
            return

        handler = self._modes.get(state)
        if handler is not None:
            handler.on_arc_delta(ring_idx, delta)
        else:
            LOGGER.error("Unknown state: %s", state)

    def on_arc_ready(self) -> None:
        """
        Arc デバイスが接続されたときに呼び出されるコールバック。
        """
        self._on_arc_ready()  # type: ignore
        self.ready_mode.on_arc_ready(self.arc)
        LOGGER.info("Arc ready")

    def on_arc_disconnect(self) -> None:
        """
        Arc デバイスが切断されたときに呼び出されるコールバック。"""
        self._on_arc_disconnect()  # type: ignore
        self.disconnect_mode.on_arc_disconnect()
        LOGGER.info("Arc disconnected")

    # ---------------------------------
    # private methods
    # ---------------------------------
    def _on_key_pressed(self) -> None:
        """
        押下イベント発生時の内部処理。

        - 押下フラグを立てる
        - 長押し判定用タイマーを開始
        - ステートマシンを押下トリガ (`press`) に遷移させる
        """
        self._is_pressed = True
        self._start_long_press_timer()
        self.press()  # type: ignore

    def _on_key_released(self) -> None:
        """
        離上イベント発生時の内部処理。

        - 押下フラグを下げる
        - ステートマシンを離上トリガ (`release`) に遷移させる
        - 長押し判定用タイマーをキャンセル
        """
        self._is_pressed = False
        self.release()  # type: ignore
        self._cancel_long_press_timer()

    def _start_long_press_timer(self) -> None:
        """
        長押し判定用タイマーを 0.5 秒で開始する。
        既存のタイマーがあればキャンセルしてから新たに開始する。
        """
        self._cancel_long_press_timer()
        loop = asyncio.get_running_loop()
        self._long_press_timer = loop.call_later(0.2, self._on_long_press)

    def _cancel_long_press_timer(self) -> None:
        """
        起動中の長押し判定用タイマーがあればキャンセルする。
        """
        if self._long_press_timer is not None:
            self._long_press_timer.cancel()
            self._long_press_timer = None

    def _on_long_press(self) -> None:
        """
        0.5 秒経過後も押下状態が継続している場合に長押しイベントを発火させる。
        """
        if self._is_pressed:
            self.long_press()  # type: ignore
            self._cancel_long_press_timer()

    # ---------------------------------
    # state callbacks
    # ---------------------------------
    def _on_enter_layer_select(self, event: EventData) -> None:  # noqa: D401
        self.layer_select_mode.on_enter()

    def _on_exit_layer_select(self, event: EventData) -> None:  # noqa: D401
        self.layer_select_mode.on_exit()

    def _on_enter_preset_select(self, event: EventData) -> None:  # noqa: D401
        self.preset_select_mode.on_enter()

    def _on_exit_preset_select(self, event: EventData) -> None:  # noqa: D401
        """PresetSelectMode を抜けるたびに累積 Δ をリセットする。"""
        self.preset_select_mode.on_exit()
