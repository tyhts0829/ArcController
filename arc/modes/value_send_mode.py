"""
mode.value_send_mode
--------------------

`ValueSendMode` は通常操作時のリング入力を処理し、LED・モデルを更新するモード。

* LFO が無効 (:pyattr:`src.enums.enums.LfoStyle.STATIC`) のリングでは回転量を
  値へ直接加算して :pyattr:`src.model.model.RingState.current_value` を更新
* LFO が有効なリングでは周波数パラメータ (:pyattr:`RingState.lfo_frequency`) を変更
* いずれの場合も :class:`renderer.led_renderer.LedRenderer` で LED を即時更新する
"""

import monome

from arc.enums.enums import LfoStyle, ValueStyle
from arc.models.model import Model
from arc.modes.base_mode import BaseMode
from arc.services.renderers.led_renderer import LedRenderer
from arc.services.sender.control_sender import AiOscSender, MidiSender


class ValueSendMode(BaseMode):
    """通常操作モード。

    Arc のリング回転に応じて :class:`src.model.model.RingState` を更新し、
    LEDRenderer へ反映する。

    Args:
        model (Model): アプリケーション状態モデル。
        led_renderer (LedRenderer): LED 描画を担当するレンダラ。
        midi_sender (MidiSender): MIDI 送信ユーティリティ。
        osc_sender (AiOscSender | None): OSC 送信ユーティリティ。
        osc_address_prefix (str | None): OSC アドレスのプレフィックス。
    """

    def __init__(
        self,
        model: Model,
        led_renderer: LedRenderer,
        midi_sender: MidiSender,
        osc_sender: AiOscSender | None = None,
        osc_address_prefix: str | None = None,
    ) -> None:
        """依存オブジェクトを保持するのみ。"""
        self.model = model
        self.led_renderer = led_renderer
        self.midi_sender = midi_sender
        self.osc_sender = osc_sender
        self.osc_address_prefix = osc_address_prefix or "/arc"

    def on_arc_ready(self, arc: monome.Arc) -> None:
        """ValueSendMode では接続イベントを無視する。

        Args:
            arc (monome.Arc): 接続された Arc デバイス。
        """
        pass

    def on_arc_disconnect(self) -> None:
        """デバイス切断イベントを無視する。"""
        pass

    def on_arc_key(self, x: int, pressed: bool) -> None:
        """キー入力を無視する。"""
        pass

    def on_arc_delta(self, ring_idx: int, delta: int) -> None:
        """リング回転を処理し、値または LFO 周波数を更新して LED を再描画する。

        Args:
            ring_idx (int): 回転したリング番号 (0‒3)。
            delta (int): 回転量。時計回りが正、反時計回りが負。
        """
        ring_state = self.model[ring_idx]
        if ring_state.lfo_style == LfoStyle.STATIC:
            ring_state.apply_delta(delta)
            # STATIC の場合のみ手動操作時に MIDI/OSC 送信
            self._send_if_needed(ring_idx, ring_state)
        else:
            ring_state.apply_lfo_delta(delta)
            # LFO が有効な場合は LFOEngine が常時送信するため、ここでは送信しない
        self.led_renderer.render_value(ring_idx, ring_state)

    def _send_if_needed(self, ring_idx: int, ring_state) -> None:
        """MIDI CC および OSC を送信する内部ヘルパー。"""
        # MIDI送信
        if ring_state.value_style == ValueStyle.MIDI_14BIT:
            self.midi_sender.send_cc_14bit(ring_state.cc_number, ring_state.value)
        elif ring_state.value_style == ValueStyle.MIDI_7BIT:
            self.midi_sender.send_cc_7bit(ring_state.cc_number, ring_state.value)
        
        # OSC送信
        if self.osc_sender:
            layer_idx = self.model.active_layer_idx
            address = f"{self.osc_address_prefix}/layer/{layer_idx}/ring/{ring_idx}/value"
            self.osc_sender.send_float(address, ring_state.value)
