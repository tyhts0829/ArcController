# main.py

import asyncio
import logging
import multiprocessing

from omegaconf import DictConfig, ListConfig

from src.controller.controller import Controller
from src.enums.enums import Mode
from src.model.model import Model
from src.modes.disconnect_mode import DisconnectMode
from src.modes.layer_select_mode import LayerSelectMode
from src.modes.preset_select_mode import PresetSelectMode
from src.modes.ready_mode import ReadyMode
from src.modes.value_send_mode import ValueSendMode
from src.services.lfo.lfo_engine import LFOEngine
from src.services.renderer.led_renderer import LedRenderer
from src.services.sender.control_sender import MidiSender
from src.utils.util import config_loader, setup_logging, setup_serialosc

LOGGER = logging.getLogger(__name__)


async def main(cfg: DictConfig | ListConfig) -> None:
    """アプリケーションを非同期的に動作させるメイン処理。

    Args:
        cfg (OmegaConf): 設定ファイルの内容を保持する `OmegaConf` オブジェクト。
    """
    loop = asyncio.get_running_loop()
    model = Model.from_config(cfg)
    led_renderer = LedRenderer(max_brightness=cfg.services.led_renderer.max_brightness)
    midi_sender = MidiSender()
    lfo_engine = LFOEngine(
        model=model, led_renderer=led_renderer, midi_sender=midi_sender, fps=cfg.services.lfo_engine.fps
    )
    ready_mode = ReadyMode(model=model, led_renderer=led_renderer, lfo_engine=lfo_engine)
    value_send_mode = ValueSendMode(model=model, led_renderer=led_renderer, midi_sender=midi_sender)
    layer_select_mode = LayerSelectMode(model=model, led_renderer=led_renderer)
    disconnect_mode = DisconnectMode(lfo_engine=lfo_engine)
    preset_select_mode = PresetSelectMode(
        model=model,
        threshold=cfg.mode.preset_select_mode.threshold,
        led_renderer=led_renderer,
    )
    mode_mapping = {
        Mode.VALUE_SEND_MODE: value_send_mode,
        Mode.LAYER_SELECT_MODE: layer_select_mode,
        Mode.PRESET_SELECT_MODE: preset_select_mode,
        Mode.DISCONNECT_MODE: disconnect_mode,
        Mode.READY_MODE: ready_mode,
    }
    app = Controller(
        model=model,
        mode_mapping=mode_mapping,
    )

    serialosc = setup_serialosc(app)
    await serialosc.connect()
    try:
        # 実行をブロックし続けたい場合の簡易的な方法
        await loop.create_future()
    except asyncio.CancelledError:
        pass
    finally:
        LOGGER.info("Shutting down: stopping LFO and turning off LEDs")
        await lfo_engine.stop()
        led_renderer.all_off()


def _sync_run() -> None:
    """設定ファイルの読み込みやログ設定などを行った上でアプリケーションを実行する同期版関数。

    他のモジュールからインポートして呼び出しやすいように用意する。
    """
    cfg = config_loader()
    level_name = cfg.globals.logging.level.upper()  # type: ignore
    log_level = getattr(logging, level_name, logging.WARNING)
    setup_logging(level=log_level)

    try:
        asyncio.run(main(cfg))
    except KeyboardInterrupt:
        LOGGER.info("Received exit signal, shutting down application")


def run(detach: bool = True):
    """Controller を起動するユーティリティ関数。

    クリエーティブコーディング側では::

        import arc
        proc = arc.run()  # 非同期で起動、以後ブロッキングしない

    と書くだけで、内部的に別プロセスとして Controller が立ち上がる。

    Args:
        detach (bool, optional): True の場合はデーモン子プロセスとして起動し、
            `multiprocessing.Process` オブジェクトを返す。False の場合は
            現在のプロセスをブロックして `_sync_run()` を実行する。

    Returns:
        multiprocessing.Process | None: detach=True なら起動した子プロセス、
            False なら None。
    """
    if detach:
        proc = multiprocessing.Process(target=_sync_run, daemon=True)
        proc.start()
        return proc
    _sync_run()
    return None


if __name__ == "__main__":
    _sync_run()
