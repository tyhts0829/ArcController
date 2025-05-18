"""mode.ready_mode
------------------

ReadyMode は Arc デバイスが *ready*（接続完了）になった直後に一度だけ呼び出される
初期化用モードです。LEDRenderer にデバイスを紐付け、LED を全消灯し、LFO エンジンを
起動するだけなので、キー／リング入力は無視します。
"""

from __future__ import annotations

import monome

from services.lfo.lfo_engine import LfoEngine
from services.renderer.led_renderer import LedRenderer
from src.model.model import Model
from src.modes.base_mode import BaseMode


class ReadyMode(BaseMode):
    """Arc 接続直後の初期化処理を担当するモード。

    * LedRenderer に Arc インスタンスを紐付け、全 LED を消灯
    * LfoEngine を起動してアニメーションを開始
    * 初回フレームを強制描画して UI を即時更新

    Args:
        model (Model): アプリケーション状態モデル。
        led_renderer (LedRenderer): LED 描画を担当するレンダラ。
        lfo_engine (LfoEngine): LED アニメーションを生成するエンジン。
    """

    def __init__(self, model: Model, led_renderer: LedRenderer, lfo_engine: LfoEngine) -> None:
        """依存オブジェクトを保持するのみで副作用は発生させない。"""
        self._model = model
        self._led_renderer = led_renderer
        self._lfo_engine = lfo_engine

    # ------------------------------------------------------------------
    # public callbacks (BaseMode interface)
    # ------------------------------------------------------------------
    def on_arc_ready(self, arc: monome.Arc) -> None:
        """Arc が接続された直後に呼ばれる。

        Args:
            arc (monome.Arc): 接続された Arc デバイス。
        """
        # デバイスを LedRenderer に DI し、クリーンな状態から開始
        self._led_renderer.set_arc(arc)
        self._led_renderer.all_off()
        # LFO アニメーションをスタート
        self._lfo_engine.start()
        # 初回のrendering を行う

        for layer in self._model:
            for ring_idx, ring_state in enumerate(layer):
                self._led_renderer.render_value(ring_idx, ring_state)

    def on_arc_disconnect(self) -> None:
        """ReadyMode では切断イベントを無視する。"""
        pass

    def on_arc_delta(self, ring_idx: int, delta: int) -> None:
        """ReadyMode ではリング回転イベントを無視する。"""
        pass

    def on_arc_key(self, x: int, pressed: bool) -> None:
        """ReadyMode ではキー入力を無視する。"""
        pass
