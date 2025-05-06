import asyncio
import logging

from controller.controller import ArcController
from controller.led_renderer import LedRenderer
from controller.lfo_engine import LfoEngine
from controller.value_processor import ValueProcessor
from model.model import Model
from util.util import setup_logging, setup_serialosc


async def main() -> None:
    loop = asyncio.get_running_loop()
    model = Model()
    value_processor = ValueProcessor()
    led_renderer = LedRenderer()
    lfo_engine = LfoEngine(model, led_renderer)
    app = ArcController(
        model=model,
        value_processor=value_processor,
        led_renderer=led_renderer,
        lfo_engine=lfo_engine,
    )
    serialosc = setup_serialosc(app)
    await serialosc.connect()
    await loop.create_future()


if __name__ == "__main__":
    setup_logging(level=logging.DEBUG)
    asyncio.run(main())
