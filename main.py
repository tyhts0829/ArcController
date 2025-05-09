import asyncio
import logging

from controller.controller import ArcController
from controller.delta_processor import DeltaProcessor
from controller.led_renderer import LedRenderer
from controller.lfo_engine import LfoEngine
from model.model import Model
from util.util import config_loader, setup_logging, setup_serialosc


async def main(cfg) -> None:
    loop = asyncio.get_running_loop()
    model = Model()
    value_processor = DeltaProcessor()
    led_renderer = LedRenderer(max_brightness=cfg.globals.led_renderer.max_brightness)
    lfo_engine = LfoEngine(model, led_renderer, fps=cfg.globals.lfo_engine.fps)
    app = ArcController(
        model=model,
        value_processor=value_processor,
        led_renderer=led_renderer,
        lfo_engine=lfo_engine,
        value_gain=cfg.globals.controller.value_gain,
        lfo_freq_gain=cfg.globals.controller.lfo_freq_gain,
    )
    serialosc = setup_serialosc(app)
    await serialosc.connect()
    await loop.create_future()


if __name__ == "__main__":
    cfg = config_loader()
    level_name = cfg.globals.logging.level.upper()
    log_level = getattr(logging, level_name, logging.WARNING)
    setup_logging(level=log_level)
    asyncio.run(main(cfg))
