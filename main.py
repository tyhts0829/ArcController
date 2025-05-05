import asyncio

from controller.controller import ArcController
from controller.led_renderer import LedRenderer
from controller.lfo_engine import LfoEngine
from controller.value_processor import ValueProcessor
from model.model import Model
from util.util import setup_logging, setup_serialosc


async def main() -> None:
    loop = asyncio.get_running_loop()
    app = ArcController(
        model=Model(),
        value_processor=ValueProcessor(),
        led_renderer=LedRenderer(),
    )
    serialosc = setup_serialosc(app)
    await serialosc.connect()
    await loop.create_future()


if __name__ == "__main__":
    setup_logging()
    asyncio.run(main())
