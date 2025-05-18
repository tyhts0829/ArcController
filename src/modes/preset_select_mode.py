from __future__ import annotations

import math
from collections import defaultdict

import monome

from renderer.led_renderer import LedRenderer
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
        self.led_renderer.set_render_block(blocked=False)
        self.led_renderer.render_value(ring_idx, self.model[ring_idx])
        acc = self._acc_deltas[ring_idx] + delta  # 累積値を更新
        steps = math.trunc(acc / self.threshold)  # ステップ数を計算
        self._acc_deltas[ring_idx] = acc - steps * self.threshold  # 残余を保持
        if steps == 0:
            return
        ring_state = self.model[ring_idx]
        ring_state.cycle_preset(steps)
        self.led_renderer.render_layer(self.model.active_layer, ignore_cache=True)

    def _reset_acc(self) -> None:
        """すべてのリングの累積 Δ をリセットする。"""
        self._acc_deltas.clear()

    def on_enter(self) -> None:
        """レイヤー選択モードに入る際の処理"""
        self.led_renderer.set_render_block(blocked=True)
        self.model.cycle_layer(-1)
        self.led_renderer.highlight(self.model.active_layer_idx)

    def on_exit(self) -> None:
        """レイヤー選択モードから出る際の処理"""
        self._reset_acc()
        self.led_renderer.set_render_block(blocked=False)
        self.led_renderer.render_layer(self.model.active_layer, ignore_cache=True)
