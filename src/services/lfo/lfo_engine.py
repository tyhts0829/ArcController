"""
controller.lfo_engine
---------------------

asyncio タスクとして動作し、各リングの LFO を計算して LED を更新するエンジン。
"""

import asyncio
import logging

from services.lfo.lfo_styles import LFO_STYLE_MAP, BaseLfoStyle, get_lfo_instance
from services.renderer.led_renderer import LedRenderer
from src.enums.enums import LfoStyle
from src.model.model import Model, RingState

LOGGER = logging.getLogger(__name__)


class LFOEngine:
    """
    asyncio タスクで動く LFO エンジン。

    Args:
        model (Model): LED 描画対象となるデータモデル。
        led_renderer (LedRenderer): LED を描画するクラス。
        fps (int): 1 秒あたりの更新フレーム数。

    `stop()` は `async` メソッドとなり、呼び出し側が `await` することで完全停止を保証できます。
    """

    def __init__(self, model: Model, led_renderer: LedRenderer, fps: int):
        """依存オブジェクトを受け取り、LFO エンジンを初期化する。

        Args:
            model (Model): LED 描画対象となるデータモデル。
            led_renderer (LedRenderer): LED を描画するクラス。
            fps (int): 1 秒あたりの更新フレーム数。
        """
        self.model = model
        self.led_renderer = led_renderer
        self.fps = fps
        self._running: bool = False
        self._task: asyncio.Task | None = None
        # 各レイヤー・リングごとに保持する LFO
        self._lfos_on_model: dict[tuple[int, int], BaseLfoStyle] = {}

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    def start(self) -> None:
        """イベントループに LFO タスクを登録して走らせる。

        二重起動を避けるため、すでに実行中なら何もしない。
        """
        LOGGER.info("LfoEngine: starting")
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        """LFO タスクをキャンセルして完全に停止する。

        Notes:
            * `CancelledError` を握りつぶして安全に終了を待つ。
            * 呼び出し側は `await engine.stop()` で完全停止を保証できる。
        """
        LOGGER.info("LfoEngine: stopping")
        self._running = False

        if self._task is None:  # そもそも起動していない
            return

        self._task.cancel()
        try:
            await self._task  # CancelledError を待って完全終了
        except asyncio.CancelledError:
            # _loop 内で CancelledError が発生した場合はここへ来る
            pass
        finally:
            self._task = None

    # ---------------------------------------------------------------------
    # 内部: メインループ
    # ---------------------------------------------------------------------
    async def _loop(self) -> None:
        """内部コルーチン: FPS に従って各リングの LFO を更新し、LED を描画し続ける。

        フレーム処理時間の揺らぎによる累積ドリフトを防ぐため、次フレーム予定時刻
        ``target`` を保持し、ループの最後に
        ``await asyncio.sleep(max(0, target - loop.time()))`` で待機する。
        更新が遅延して ``sleep`` 時刻を過ぎていた場合は ``target`` を現在時刻へ
        リセットして追いつく。
        """
        frame_interval = 1.0 / self.fps
        loop = asyncio.get_running_loop()
        prev = loop.time()
        target = prev  # 次フレーム予定時刻

        try:
            while self._running:
                now = loop.time()
                dt = now - prev
                prev = now

                # ----- LFO 更新 & LED 描画 --------------------------------
                for layer_idx, layer in enumerate(self.model):
                    for ring_idx, ring_state in enumerate(layer):
                        self._update_ring(layer_idx, ring_idx, ring_state, dt)

                # ----- FPS 制御: ドリフト補正あり -------------------------
                target += frame_interval
                sleep_for = target - loop.time()

                if sleep_for < -frame_interval:
                    # フレーム処理が大幅に遅延している場合は target をリセット
                    target = loop.time()
                    sleep_for = 0.0

                await asyncio.sleep(max(0.0, sleep_for))
        except asyncio.CancelledError:
            # stop() が呼ばれたときにここへ来る
            pass

    # -----------------------------------------------------------------
    # 内部: ヘルパーメソッド
    # -----------------------------------------------------------------
    def _get_or_create_lfo(self, key: tuple[int, int], ring_state) -> BaseLfoStyle:
        """キーに対応する LFO インスタンスを取得または生成する。"""
        expected_cls = LFO_STYLE_MAP.get(ring_state.lfo_style)
        lfo = self._lfos_on_model.get(key)

        # スタイルが変わったらインスタンスを作り直す
        if lfo is None or lfo.__class__ is not expected_cls:
            before_style = None if lfo is None else lfo.style_enum
            LOGGER.info(
                "LFO style changed, re-instantiating. before=%s, after=%s",
                before_style,
                ring_state.lfo_style,
            )
            lfo = get_lfo_instance(ring_state.lfo_style)
            self._lfos_on_model[key] = lfo
        return lfo

    def _update_ring(self, layer_idx: int, ring_idx: int, ring_state: RingState, dt: float) -> None:
        """単一リングの値を更新し、必要なら LED を描画する。"""
        if ring_state.lfo_style == LfoStyle.STATIC:
            return

        key = (layer_idx, ring_idx)
        lfo = self._get_or_create_lfo(key, ring_state)

        # 値更新
        ring_state.current_value = lfo.update(ring_state, dt)

        # アクティブレイヤーのみ LED 描画
        if layer_idx == self.model.active_layer_idx:
            self.led_renderer.render_value(ring_idx, ring_state)
