"""
controller.lfo_engine
---------------------

asyncio タスクとして動作し、各リングの LFO を計算して LED を更新するエンジン。
"""

import asyncio
import logging

from lfo.lfo_styles import LFO_STYLE_MAP, BaseLfoStyle, get_lfo_instance
from renderer.led_renderer import LedRenderer
from src.enums.enums import LfoStyle
from src.model.model import Model

LOGGER = logging.getLogger(__name__)


class LfoEngine:
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
        """内部コルーチン: FPS に従って各リングの LFO を更新し、LED を描画し続ける。"""
        frame_interval = 1.0 / self.fps
        loop = asyncio.get_running_loop()
        prev = loop.time()

        try:
            while self._running:
                frame_start = loop.time()
                dt = frame_start - prev
                prev = frame_start

                # ----- LFO 更新 & LED 描画 --------------------------------
                for layer_idx, layer in enumerate(self.model):
                    for ring_idx, ring_state in enumerate(layer):
                        # LFO が STATIC の場合はスキップ
                        if ring_state.lfo_style == LfoStyle.STATIC:
                            continue

                        key = (layer_idx, ring_idx)
                        expected_cls = LFO_STYLE_MAP.get(ring_state.lfo_style)
                        lfo = self._lfos_on_model.get(key)

                        # スタイル変更時はインスタンスを作り直す
                        if lfo is None or lfo.__class__ is not expected_cls:
                            before_style = None if lfo is None else lfo.style_enum
                            LOGGER.info(
                                "LFO style changed, re-instantiating. before=%s, after=%s",
                                before_style,
                                ring_state.lfo_style,
                            )
                            lfo = get_lfo_instance(ring_state.lfo_style)
                            self._lfos_on_model[key] = lfo

                        # 値更新
                        ring_state.current_value = lfo.update(ring_state, dt)

                        # アクティブレイヤーのみ LED 描画
                        if layer_idx == self.model.active_layer_idx:
                            self.led_renderer.render_value(ring_idx, ring_state)

                # ----- FPS 制御 ------------------------------------------
                elapsed = loop.time() - frame_start
                sleep_for = frame_interval - elapsed
                # 0 以下でも 0 秒 sleep して制御権を戻す
                await asyncio.sleep(max(0, sleep_for))
        except asyncio.CancelledError:
            # stop() が呼ばれたときにここへ来る
            pass
