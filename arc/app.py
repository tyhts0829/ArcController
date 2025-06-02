"""
ArcController アプリケーションのメイン実装

このモジュールは、Monome Arcデバイス用のMIDIコントローラーアプリケーションの
メイン処理を提供します。
"""

import asyncio
import logging

from omegaconf import DictConfig, ListConfig

from arc.controller.controller import Controller
from arc.enums.enums import Mode
from arc.models.model import Model
from arc.modes.disconnect_mode import DisconnectMode
from arc.modes.layer_select_mode import LayerSelectMode
from arc.modes.preset_select_mode import PresetSelectMode
from arc.modes.ready_mode import ReadyMode
from arc.modes.value_send_mode import ValueSendMode
from arc.services.lfo.lfo_engine import LFOEngine
from arc.services.renderers.led_renderer import LedRenderer
from arc.services.sender.control_sender import MidiSender
from arc.utils.util import config_loader, setup_logging, setup_serialosc

LOGGER = logging.getLogger(__name__)


async def main(cfg: DictConfig | ListConfig) -> None:
    """アプリケーションを非同期的に動作させるメイン処理。

    Args:
        cfg (OmegaConf): 設定ファイルの内容を保持する `OmegaConf` オブジェクト。
    """
    loop = asyncio.get_running_loop()
    model = Model.from_config(cfg)
    led_renderer = LedRenderer(max_brightness=cfg.services.led_renderer.max_brightness)

    # MIDI設定を取得
    midi_config = cfg.senders.midi
    midi_sender = MidiSender(port_name=midi_config.port_name, channel=midi_config.channel, enabled=midi_config.enabled)
    midi_sender.start()
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
        long_press_duration=cfg.controller.long_press_duration,
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
        midi_sender.stop()


def run() -> None:
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


if __name__ == "__main__":
    run()
