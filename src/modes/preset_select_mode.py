from __future__ import annotations

import math
from collections import defaultdict

import monome

from src.controller.led_renderer import LedRenderer
from src.model.model import Model
from src.modes.base_mode import BaseMode


class PresetSelectMode(BaseMode):
    def __init__(self, model: Model, threshold: int, led_renderer: LedRenderer) -> None:
        self.model = model
        self.threshold = threshold
        self.led_renderer = led_renderer
        self._acc_deltas = defaultdict(int)

    def on_arc_ready(self, arc: monome.Arc) -> None:
        pass

    def on_arc_disconnect(self) -> None:
        pass

    def on_arc_key(self, x: int, pressed: bool) -> None:
        pass

    def on_arc_delta(self, ring_idx: int, delta: int) -> None:
        acc = self._acc_deltas[ring_idx] + delta  # 累積値を更新
        steps = math.trunc(acc / self.threshold)  # ステップ数を計算
        self._acc_deltas[ring_idx] = acc - steps * self.threshold  # 残余を保持
        if steps == 0:
            return
        ring_state = self.model[ring_idx]
        ring_state.cycle_preset(steps)
        self.led_renderer.render_layer(self.model.active_layer, force=True)

    def reset_acc(self) -> None:
        """すべてのリングの累積 Δ をリセットする。"""
        self._acc_deltas.clear()

    def set_render_block(self, block: bool) -> None:
        self.led_renderer.set_render_block(block)

    def cycle_layer(self, steps: int = 1) -> None:
        """レイヤーを指定されたステップ数だけサイクルする。"""
        self.model.cycle_layer(steps)
        self.led_renderer.highlight(self.model.active_layer_idx)
        self.led_renderer.set_render_block(True)  # lfo_engine.py による描画をブロッ
