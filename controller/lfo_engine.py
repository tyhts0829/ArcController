import asyncio

from controller.led_renderer import LedRenderer
from enums.enums import LfoStyle
from model.model import Model


class LfoEngine:
    """
    asyncio タスクで動く LFO エンジン。
    `start()` で task を起動し、`stop()` でキャンセルする。
    """

    def __init__(self, model: Model, led_renderer: LedRenderer, fps: int = 60):
        self.model = model
        self.led_renderer = led_renderer
        self.fps = fps
        self._running: bool = False
        self._task: asyncio.Task | None = None
        self.speed = 0.0005

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    def start(self) -> None:
        """イベントループ上に LFO タスクを登録して走らせる"""
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._loop())

    def stop(self) -> None:
        """タスクを取り消して終了させる"""
        self._running = False
        if self._task is not None:
            self._task.cancel()

    # ---------------------------------------------------------------------
    # 内部: メインループ
    # ---------------------------------------------------------------------
    async def _loop(self) -> None:
        frame_interval = 1.0 / self.fps
        loop = asyncio.get_running_loop()
        prev = loop.time()

        try:
            while self._running:
                frame_start = loop.time()
                dt = frame_start - prev
                prev = frame_start

                # ----- Ring ごとの更新 -----------------------------------
                for ring_number, ring_state in enumerate(self.model.rings):
                    if ring_state.lfo_style != LfoStyle.STATIC:
                        ring_state.current_value = ring_state.lfo_strategy.update(ring_state, dt)
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
