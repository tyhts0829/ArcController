"""
controller.controller
---------------------

monome Arc デバイスからの入力イベントを Model / LED / LFO へ橋渡しする
コントローラクラスを定義するモジュール。
"""

import logging

import monome
from controller.delta_processor import DeltaProcessor
from controller.led_renderer import LedRenderer
from controller.lfo_engine import LfoEngine
from controller.preset_manager import PresetManager
from enums.enums import LfoStyle
from model.model import Model, RingState

LOGGER = logging.getLogger(__name__)


class ArcController(monome.ArcApp):
    """
    monome.ArcApp を継承し、リング回転とキー押下を受け取って
    Model・LedRenderer・LfoEngine を協調させるコントローラ。

    Args:
        model (Model): 各リングの状態を保持するデータモデル。
        value_processor (DeltaProcessor): ring Δ を値へ変換する処理クラス。
        led_renderer (LedRenderer): RingState を LED へ描画するクラス。
        lfo_engine (LfoEngine): 非同期で LFO を駆動し LED を更新するエンジン。
        presets (list[dict]): プリセット定義のリスト。
        preset_threshold (int): プリセット切替に必要な ring Δ のしきい値。
        value_gain (float): ring Δ を値へスケーリングする係数。
        lfo_freq_gain (float): ring Δ を LFO 周波数へスケーリングする係数。
    """

    def __init__(
        self,
        model: Model,
        value_processor: DeltaProcessor,
        led_renderer: LedRenderer,
        lfo_engine: LfoEngine,
        preset_manager: PresetManager,
        value_gain: float,
        lfo_freq_gain: float,
    ) -> None:
        """依存オブジェクトを受け取り、内部状態を初期化する。

        Args:
            model (Model): 各リングの状態を保持するデータモデル。
            value_processor (DeltaProcessor): ring Δ を値へ変換する処理クラス。
            led_renderer (LedRenderer): RingState を LED へ描画するクラス。
            lfo_engine (LfoEngine): 非同期で LFO を駆動し LED を更新するエンジン。
            presets (list[dict]): プリセット定義のリスト。
            preset_threshold (int): プリセット切替に必要な ring Δ のしきい値。
            value_gain (float): ring Δ を値へスケーリングする係数。
            lfo_freq_gain (float): ring Δ を LFO 周波数へスケーリングする係数。
        """
        super().__init__()
        self.model = model
        self.delta_processor = value_processor
        self.led_renderer = led_renderer
        self.lfo_engine = lfo_engine
        self.preset_manager = preset_manager
        self._key_pressed = False
        self.value_gain = value_gain
        self.lfo_freq_gain = lfo_freq_gain

    def on_arc_ready(self) -> None:
        """Arc が接続され準備完了になったときに呼ばれる。LED を消灯し LFO を開始。"""
        LOGGER.info("Arc ready")
        self.led_renderer.set_arc(self.arc)  # DIのためself.arcをここでセットする関数呼び出し
        self.led_renderer.all_off()
        self.lfo_engine.start()

    def on_arc_disconnect(self) -> None:
        """Arc が切断されたときに呼ばれる。LED を消灯し LFO を停止。"""
        LOGGER.info("Arc disconnected")
        self.led_renderer.all_off()
        self.lfo_engine.stop()

    def on_arc_delta(self, ring_idx: int, delta: int) -> None:
        """リング回転 (Δ) イベントを処理する。

        キー押下状態に応じてプリセット切替またはリング値/LFO 周波数を更新する。

        Args:
            ring_idx (int): 対象リングのインデックス (0‒3)。
            delta (int): エンコーダが発生させた増分値 (正負)。
        """
        LOGGER.debug("Ring %d Δ%+d", ring_idx, delta)
        ring_state = self.model[ring_idx]

        if self._key_pressed:
            changed = self.preset_manager.process_delta(ring_idx, delta, ring_state)
            if changed:
                self.led_renderer.render_value(ring_idx, ring_state)
            return

        self._update_ring_state(ring_idx, delta, ring_state)

    # ---------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------

    def _update_ring_state(self, ring_idx: int, delta: int, ring_state: RingState) -> None:
        """リングの現在値または LFO 周波数を更新し、LED を再描画する内部ヘルパ。

        Args:
            ring_idx (int): リングインデックス。
            delta (int): 今回の増分 Δ。
            ring_state (RingState): 対象リングの状態。
        """
        if ring_state.lfo_style == LfoStyle.STATIC:
            scaled_delta = delta * self.value_gain
            ring_state.current_value = self.delta_processor.update_value(ring_state, scaled_delta)
        else:
            scaled_delta = delta * self.lfo_freq_gain
            ring_state.lfo_frequency = self.delta_processor.update_frequency(ring_state, scaled_delta)

        self.led_renderer.render_value(ring_idx, ring_state)

    def on_arc_key(self, x: int, s: bool) -> None:
        """Arc 本体のキー押下/離上イベントを処理し、プリセット切替用 Δ をリセットする。

        Args:
            x (int): キー位置 (Arc は常に 0)。
            s (bool): 押下状態。True で押下、False で離上。
        """
        self._key_pressed = s
        action = "pressed" if s else "released"
        LOGGER.debug("key %s", action)
        if not s:
            self.preset_manager.reset()
