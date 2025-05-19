import asyncio
import logging

from omegaconf import DictConfig, ListConfig

from services.lfo.lfo_engine import LfoEngine
from services.renderer.led_renderer import LedRenderer
from src.controller.controller import ArcController
from src.model.model import Model
from src.modes.disconnect_mode import DisconnectMode
from src.modes.layer_select_mode import LayerSelectMode
from src.modes.preset_select_mode import PresetSelectMode
from src.modes.ready_mode import ReadyMode
from src.modes.value_send_mode import ValueSendMode
from src.utils.util import config_loader, setup_logging, setup_serialosc

LOGGER = logging.getLogger(__name__)


async def main(cfg: DictConfig | ListConfig) -> None:
    """アプリケーションのメインエントリーポイント。

    Args:
        cfg (OmegaConf): 設定ファイルの内容を保持する `OmegaConf` オブジェクト。
    """
    loop = asyncio.get_running_loop()
    model = Model.from_config(cfg)
    led_renderer = LedRenderer(max_brightness=cfg.services.led_renderer.max_brightness)
    lfo_engine = LfoEngine(model=model, led_renderer=led_renderer, fps=cfg.services.lfo_engine.fps)
    ready_mode = ReadyMode(model=model, led_renderer=led_renderer, lfo_engine=lfo_engine)
    value_send_mode = ValueSendMode(model=model, led_renderer=led_renderer)
    layer_select_mode = LayerSelectMode(model=model, led_renderer=led_renderer)
    disconnect_mode = DisconnectMode(lfo_engine=lfo_engine)
    preset_select_mode = PresetSelectMode(
        model=model,
        threshold=cfg.mode.preset_select_mode.threshold,
        led_renderer=led_renderer,
    )
    app = ArcController(
        model=model,
        ready_mode=ready_mode,
        value_send_mode=value_send_mode,
        layer_select_mode=layer_select_mode,
        preset_select_mode=preset_select_mode,
        disconnect_mode=disconnect_mode,
    )

    serialosc = setup_serialosc(app)
    await serialosc.connect()
    try:
        await loop.create_future()
    except asyncio.CancelledError:
        pass
    finally:
        LOGGER.info("Shutting down: stopping LFO and turning off LEDs")
        await lfo_engine.stop()
        led_renderer.all_off()


if __name__ == "__main__":
    cfg = config_loader()
    level_name = cfg.globals.logging.level.upper()  # type: ignore
    log_level = getattr(logging, level_name, logging.WARNING)
    setup_logging(level=log_level)
    try:
        asyncio.run(main(cfg))
    except KeyboardInterrupt:
        LOGGER.info("Received exit signal, shutting down application")
