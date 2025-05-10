import logging

import monome
from controller.delta_processor import DeltaProcessor
from controller.led_renderer import LedRenderer
from controller.lfo_engine import LfoEngine
from enums.enums import LfoStyle
from model.model import Model

LOGGER = logging.getLogger(__name__)


class ArcController(monome.ArcApp):
    def __init__(
        self,
        model: Model,
        value_processor: DeltaProcessor,
        led_renderer: LedRenderer,
        lfo_engine: LfoEngine,
        value_gain: float,
        lfo_freq_gain: float,
    ) -> None:
        super().__init__()
        self.model = model
        self.delta_processor = value_processor
        self.led_renderer = led_renderer
        self.lfo_engine = lfo_engine
        self.value_gain = value_gain
        self.lfo_freq_gain = lfo_freq_gain

    def on_arc_ready(self) -> None:
        LOGGER.info("Arc ready")
        self.led_renderer.set_arc(self.arc)  # DIのためself.arcをここでセットする関数呼び出し
        self.led_renderer.all_off()
        self.lfo_engine.start()

    def on_arc_disconnect(self) -> None:
        LOGGER.info("Arc disconnected")
        self.led_renderer.all_off()
        self.lfo_engine.stop()

    def on_arc_delta(self, ring_idx: int, delta: int) -> None:
        LOGGER.debug("Ring %d Δ%+d", ring_idx, delta)
        ring_state = self.model[ring_idx]
        if ring_state.lfo_style == LfoStyle.STATIC:
            scaled_delta = delta * self.value_gain
            ring_state.current_value = self.delta_processor.update_value(ring_state, scaled_delta)
        else:
            scaled_delta = delta * self.lfo_freq_gain
            ring_state.lfo_frequency = self.delta_processor.update_frequency(ring_state, scaled_delta)
        self.led_renderer.render(ring_idx, ring_state)

    def on_arc_key(self, x: int, s: bool) -> None:
        action = "pressed" if s else "released"
        LOGGER.debug("key %s", action)
