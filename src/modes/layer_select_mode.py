"""
mode.layer_select_mode
----------------------

`LayerSelectMode` は Arc コントローラの「レイヤー選択」モードを実装するモジュール。

このモードでは Arc デバイスのキーを短押しするたびにレイヤーを 1 ステップ循環させ、
ハイライト表示で現在選択中のレイヤーをユーザへフィードバックする。キーを離すと
ブロックを解除してアクティブレイヤーの通常表示へ戻る。

主なフロー:
* :py:meth:`LayerSelectMode.on_enter` でモード遷移直後に 1 ステップ進めてハイライト
* :py:meth:`LayerSelectMode.on_arc_key` で押下/離上に応じてハイライトと再描画を制御
* :py:meth:`LayerSelectMode.on_exit` で LED 描画ブロックを解除しアクティブレイヤーを再描画
"""

from __future__ import annotations

import monome

from renderer.led_renderer import LedRenderer
from src.model.model import Model
from src.modes.base_mode import BaseMode


class LayerSelectMode(BaseMode):
    """レイヤー選択モードを表すクラス。

    Args:
        model (Model): アプリケーション状態モデル。
        led_renderer (LedRenderer): LED 描画を担当するレンダラ。

    Attributes:
        model (Model): アプリケーション状態モデル。
        led_renderer (LedRenderer): LED レンダラ。
    """

    def __init__(self, model: Model, led_renderer: LedRenderer) -> None:
        self.model = model
        self.led_renderer = led_renderer

    def on_arc_ready(self, arc: monome.Arc) -> None:
        """Arc デバイス接続完了時のコールバック。現在は特別な処理を行わない。

        Args:
            arc (monome.Arc): 接続された Arc デバイス。
        """
        pass

    def on_arc_disconnect(self) -> None:
        """Arc デバイス切断時のコールバック。現在は特別な処理を行わない。"""
        pass

    def on_arc_key(self, x: int, pressed: bool) -> None:
        """キー押下／離上イベントを処理し、レイヤー選択表示を制御する。

        Args:
            x (int): キー番号（使用しないがインターフェース準拠のため受け取る）。
            pressed (bool): 押下時 True、離上時 False。
        """
        if pressed:
            self._cycle_layer_and_highlight()
        else:
            self._refresh_active_layer_led()

    def on_arc_delta(self, ring_idx: int, delta: int) -> None:
        """レイヤー選択モードではリング回転を無視するため何もしない。"""
        pass

    def on_enter(self) -> None:
        """レイヤー選択モードへの遷移時に呼ばれる。

        - レイヤーを 1 ステップ循環
        - ハイライト表示のため LEDRenderer をブロック
        """
        self.on_arc_key(0, True)

    def on_exit(self) -> None:
        """レイヤー選択モードから抜ける際に呼ばれる。

        - LEDRenderer のブロックを解除
        - アクティブレイヤーを再描画
        """
        self._refresh_active_layer_led()

    def _cycle_layer_and_highlight(self) -> None:
        """レイヤーを 1 ステップ進め、選択レイヤーのリングを全灯ハイライトする。"""
        self.led_renderer.set_render_block(
            blocked=True
        )  # lfo_engine.py による描画をブロックし、highlightが持続するようにする
        self.model.cycle_layer(1)
        self.led_renderer.highlight(self.model.active_layer_idx)

    def _refresh_active_layer_led(self) -> None:
        """LEDRenderer を解除し、アクティブレイヤーを通常描画で更新する。"""
        self.led_renderer.set_render_block(blocked=False)
        self.led_renderer.render_layer(self.model.active_layer, ignore_cache=True)
