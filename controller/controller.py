import logging

import monome
from controller.delta_processor import DeltaProcessor
from controller.led_renderer import LedRenderer
from controller.lfo_engine import LfoEngine
from enums.enums import LfoStyle
from model.model import Model

LOGGER = logging.getLogger("ArcController")


class ArcController(monome.ArcApp):
    def __init__(
        self,
        model: Model,
        value_processor: DeltaProcessor,
        led_renderer: LedRenderer,
        lfo_engine: LfoEngine,
        value_gain: float,
        lfo_freq_gain: float,
    ):
        super().__init__()
        self.model = model
        self.delta_processor = value_processor
        self.led_renderer = led_renderer
        self.lfo_engine = lfo_engine
        self.value_gain = value_gain
        self.lfo_freq_gain = lfo_freq_gain

    def on_arc_ready(self):
        LOGGER.info("Arc ready — binding LedRenderer and clearing LEDs")
        self.led_renderer.set_arc(self.arc)  # DIのためself.arcをここでセットする関数呼び出し
        self.led_renderer.all_off()
        self.lfo_engine.start()

    def on_arc_disconnect(self):
        LOGGER.warning("Arc disconnected")
        self.led_renderer.all_off()
        self.lfo_engine.stop()

    def on_arc_delta(self, ring, delta):
        LOGGER.debug("Ring %d Δ%+d", ring, delta)
        ring_state = self.model[ring]
        if ring_state.lfo_style == LfoStyle.STATIC:
            scaled_delta = delta * self.value_gain
            ring_state.current_value = self.delta_processor.update_value(ring_state, scaled_delta)
        else:
            scaled_delta = delta * self.lfo_freq_gain
            ring_state.lfo_frequency = self.delta_processor.update_frequency(ring_state, scaled_delta)
        self.led_renderer.render(ring, ring_state)

    def on_arc_key(self, _, s):
        action = "pressed" if s else "released"
        LOGGER.info("key %s", action)
