import threading
import time

from enums.enums import LfoStyle


class LfoEngine(threading.Thread):
    """
    ベースループは 別スレッドに切り出し、他スレッドをブロックしないようにする。
    """

    def __init__(self, model, led_renderer, fps=60):
        super().__init__(daemon=True)
        self.model = model
        self.led_renderer = led_renderer
        self.fps = fps
        self._running = True
        self.speed = 0.0005  # ring_deltaに対するfrequencyの加算速度

    def run(self):
        prev = time.perf_counter()
        while self._running:
            now = time.perf_counter()
            dt = now - prev
            prev = now
            for ring_number, ring_state in enumerate(self.model.rings):
                lfo_strategy = ring_state.lfo_strategy
                if ring_state.lfo_style != LfoStyle.STATIC:
                    ring_state.current_value = lfo_strategy.update(ring_state, dt)
                    self.led_renderer.render(ring_number, ring_state)

            time.sleep(1 / self.fps)

    def stop(self):
        self._running = False
