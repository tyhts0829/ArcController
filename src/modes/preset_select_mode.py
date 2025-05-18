"""
mode.preset_select_mode
-----------------------

`PresetSelectMode` は Arc コントローラの「プリセット選択」モードを実装するモジュール。

このモードでは、各リングのエンコーダ回転量を累積し、その絶対値が ``threshold`` を
超えたタイミングで :py:meth:`src.model.model.RingState.cycle_preset` を呼び出して
プリセットを循環させる。

主なフロー:
* :py:meth:`PresetSelectMode.on_enter` で LED 描画を一時ブロックし、次に編集する
  レイヤーをハイライト表示
* :py:meth:`PresetSelectMode.on_arc_delta` で回転量を蓄積し、しきい値を超えたら
  プリセットを変更して LED を即時更新
* :py:meth:`PresetSelectMode.on_exit` でブロックを解除し、アクティブレイヤーを再描画

本モジュールが公開するパブリックシンボルは ``PresetSelectMode`` クラスのみ。
"""

from __future__ import annotations

import math
from collections import defaultdict

import monome

from renderer.led_renderer import LedRenderer
from src.model.model import Model
from src.modes.base_mode import BaseMode


class PresetSelectMode(BaseMode):
    """プリセット選択モードを表すクラス。

    Args:
        model (Model): アプリケーション共通の状態モデル。
        threshold (int): プリセットを 1 ステップ変更するのに必要なエンコーダ累積値。
        led_renderer (LedRenderer): LED 描画を担当するレンダラ。

    Attributes:
        model (Model): アプリケーションの状態モデル。
        threshold (int): プリセット変更しきい値。
        led_renderer (LedRenderer): LED レンダラ。
        _acc_deltas (defaultdict[int, int]): 各リングごとの累積 Δ 値。
    """

    def __init__(self, model: Model, threshold: int, led_renderer: LedRenderer) -> None:
        self.model = model
        self.threshold = threshold
        self.led_renderer = led_renderer
        self._acc_deltas = defaultdict(int)

    def on_arc_ready(self, arc: monome.Arc) -> None:
        """Arc デバイス接続完了時に呼び出されるコールバック。

        Args:
            arc (monome.Arc): 接続された Arc デバイス。
        """
        pass

    def on_arc_disconnect(self) -> None:
        """Arc デバイス切断時のコールバック。現在は特別な処理を行わない。"""
        pass

    def on_arc_key(self, x: int, pressed: bool) -> None:
        """Arc のキー押下／解放イベントを受け取る。

        Args:
            x (int): キー番号。PresetSelectMode では使用しない。
            pressed (bool): 押下時 True、解放時 False。
        """
        pass

    def on_arc_delta(self, ring_idx: int, delta: int) -> None:
        """エンコーダの回転イベントを処理するメインハンドラ。

        回転量を累積し、その絶対値が ``threshold`` を超えたぶんだけ
        :pyattr:`src.model.model.RingState.preset_index` を循環させる。

        Args:
            ring_idx (int): 回転したリング番号 (0‒3)。
            delta (int): 回転量。時計回りが正、反時計回りが負。
        """
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
        """プリセット選択モードへの遷移時に呼ばれる。

        - LEDRenderer の描画を一時ブロックしてハイライトを保持
        - 次に編集するレイヤーを 1 つ前へ循環
        - アクティブレイヤーのリング全灯で視覚フィードバックを行う
        """
        self.led_renderer.set_render_block(blocked=True)
        self.model.cycle_layer(-1)
        self.led_renderer.highlight(self.model.active_layer_idx)

    def on_exit(self) -> None:
        """プリセット選択モードから抜ける際に呼ばれる。

        - リングごとの累積 Δ をリセット
        - LEDRenderer のブロックを解除
        - アクティブレイヤーを再描画して最新状態を反映
        """
        self._reset_acc()
        self.led_renderer.set_render_block(blocked=False)
        self.led_renderer.render_layer(self.model.active_layer, ignore_cache=True)
