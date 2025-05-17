import monome
from controller.led_renderer import LedRenderer
from enums.enums import LfoStyle
from mode.base_mode import BaseMode
from model.model import Model


class ValueSendMode(BaseMode):
    def __init__(self, model: Model, led_renderer: LedRenderer) -> None:
        self.model = model
        self.led_renderer = led_renderer

    def on_arc_ready(self, arc: monome.Arc) -> None:
        pass

    def on_arc_disconnect(self) -> None:
        pass

    def on_arc_key(self, x: int, pressed: bool) -> None:
        pass

    def on_arc_delta(self, ring_idx: int, delta: int) -> None:
        ring_state = self.model[ring_idx]
        if ring_state.lfo_style == LfoStyle.STATIC:
            ring_state.apply_delta(delta)
        else:
            ring_state.apply_lfo_delta(delta)
        self.led_renderer.render_value(ring_idx, ring_state)
