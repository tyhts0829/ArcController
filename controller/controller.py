import logging

import monome
from controller.led_renderer import LedRenderer
from controller.value_processor import ValueProcessor
from model.model import Model

LOGGER = logging.getLogger("ArcController")


class ArcController(monome.ArcApp):
    def __init__(
        self,
        model: Model,
        value_processor: ValueProcessor,
        led_renderer: LedRenderer,
    ):
        super().__init__()
        self.model = model
        self.value_processor = value_processor
        self.led_renderer = led_renderer

    def on_arc_ready(self):
        LOGGER.info("Arc ready — binding LedRenderer and clearing LEDs")
        self.led_renderer.set_arc(self.arc)  # DIのためself.arcをここでセットする関数呼び出し
        self.led_renderer.all_off()

    def on_arc_disconnect(self):
        LOGGER.warning("Arc disconnected")

    def on_arc_delta(self, ring, delta):
        LOGGER.debug("Ring %d Δ%+d", ring, delta)
        ring_state = self.model[ring]
        ring_state.current_value = self.value_processor.apply(delta, ring_state)
        self.led_renderer.render(ring, ring_state)

    def on_arc_key(self, _, s):
        action = "pressed" if s else "released"
        LOGGER.info("key %s", action)
