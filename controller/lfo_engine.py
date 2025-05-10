"""
controller.lfo_engine
---------------------

asyncio タスクとして動作し、各リングの LFO を計算して LED を更新するエンジン。
"""

import asyncio
import logging

from controller.led_renderer import LedRenderer
from controller.lfo_styles import LFO_STYLE_MAP, BaseLfoStyle, get_lfo_instance
from model.model import Model

LOGGER = logging.getLogger(__name__)


class LfoEngine:
    """
    asyncio タスクで動く LFO エンジン。

    Args:
        model (Model): LED 描画対象となるデータモデル。
        led_renderer (LedRenderer): LED を描画するクラス。
        fps (int): 1 秒あたりの更新フレーム数。
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
        # 各リングごとに保持するLFO
        self._lfo: dict[int, BaseLfoStyle] = {}

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

    def stop(self) -> None:
        """LFO タスクをキャンセルして停止する。

        タスク未実行の場合は何もしない。
        """
        LOGGER.info("LfoEngine: stopping")
        self._running = False
        if self._task is not None:
            self._task.cancel()

    # ---------------------------------------------------------------------
    # 内部: メインループ
    # ---------------------------------------------------------------------
    async def _loop(self) -> None:
        """内部コルーチン: FPS に従って各リングの LFO を更新し、LED を描画し続ける。"""
        frame_interval = 1.0 / self.fps
        loop = asyncio.get_running_loop()
        prev = loop.time()

        try:
            while self._running:
                frame_start = loop.time()
                dt = frame_start - prev
                prev = frame_start

                # ----- Ring ごとの更新 -----------------------------------
                for ring_number, ring_state in enumerate(self.model):

                    lfo = self._lfo.get(ring_number)
                    if lfo.__class__ is not LFO_STYLE_MAP.get(ring_state.lfo_style):
                        before_style = None if lfo is None else lfo.style_enum
                        LOGGER.info(
                            f"LFO style changed, re-instantiating. before={before_style}, after={ring_state.lfo_style}"
                        )
                        # LFO スタイルが変わったら新規インスタンス化
                        lfo = get_lfo_instance(ring_state.lfo_style)
                        self._lfo[ring_number] = lfo

                    ring_state.current_value = lfo.update(ring_state, dt)
                    # LedRenderer は同期関数なのでそのまま呼ぶ
                    self.led_renderer.render(ring_number, ring_state)

                # ----- FPS 制御 ------------------------------------------
                elapsed = loop.time() - frame_start
                sleep_for = frame_interval - elapsed
                # 0 以下でも 0 秒 sleep して制御権を戻す
                await asyncio.sleep(max(0, sleep_for))
        except asyncio.CancelledError:
            # stop() が呼ばれたときにここへ来る
            pass
