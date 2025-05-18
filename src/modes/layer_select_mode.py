from __future__ import annotations

import monome

from renderer.led_renderer import LedRenderer
from src.model.model import Model
from src.modes.base_mode import BaseMode


class LayerSelectMode(BaseMode):
    def __init__(self, model: Model, led_renderer: LedRenderer) -> None:
        self.model = model
        self.led_renderer = led_renderer

    def on_arc_ready(self, arc: monome.Arc) -> None:
        pass

    def on_arc_disconnect(self) -> None:
        pass

    def on_arc_key(self, x: int, pressed: bool) -> None:
        if pressed:
            self._cycle_layer_and_highlight()
        else:
            self._refresh_active_layer_led()

    def on_arc_delta(self, ring_idx: int, delta: int) -> None:
        pass

    def on_enter(self) -> None:
        """
        レイヤー選択モードに入る際の処理
        レイヤー選択モードに入る際にレイヤーをサイクルする
        """
        self.on_arc_key(0, True)

    def on_exit(self) -> None:
        """
        レイヤー選択モードから出る際の処理
        アクティブレイヤーの LED を表示する
        """
        self._refresh_active_layer_led()

    def _cycle_layer_and_highlight(self) -> None:
        """レイヤーを指定されたステップ数だけサイクルし、LED をハイライトする。"""
        self.led_renderer.set_render_block(
            blocked=True
        )  # lfo_engine.py による描画をブロックし、highlightが持続するようにする
        self.model.cycle_layer(1)
        self.led_renderer.highlight(self.model.active_layer_idx)

    def _refresh_active_layer_led(self) -> None:
        """レイヤー選択モードの状態を更新する。"""
        self.led_renderer.set_render_block(blocked=False)
        self.led_renderer.render_layer(self.model.active_layer, ignore_cache=True)
