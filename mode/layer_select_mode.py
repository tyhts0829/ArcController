from __future__ import annotations

import monome
from controller.led_renderer import LedRenderer
from mode.base_mode import BaseMode
from model.model import Model


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
            self.cycle_layer()
        else:
            self.led_renderer.set_render_block(False)
            self.led_renderer.render_layer(self.model.active_layer, force=True)

    def cycle_layer(self, steps: int = 1) -> None:
        """レイヤーを指定されたステップ数だけサイクルする。"""
        self.model.cycle_layer(steps)
        self.led_renderer.highlight(self.model.active_layer_idx)
        self.led_renderer.set_render_block(True)  # lfo_engine.py による描画をブロックする

    def on_arc_delta(self, ring_idx: int, delta: int) -> None:
        pass
