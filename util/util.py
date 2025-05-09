import asyncio
import logging
from pathlib import Path

from omegaconf import OmegaConf

import monome

LOGGER = logging.getLogger(__name__)  # モジュール専用ロガー


def fmt(v) -> str:
    """Floats → 3桁小数、その他はそのまま文字列化"""
    return f"{v:.3f}" if isinstance(v, float) else str(v)


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def config_loader(cfg_path: Path = Path("config/config.yaml")) -> OmegaConf:
    """
    config/config.yaml を OmegaConf で読み込み、DictConfig として返す。
    """
    return OmegaConf.load(str(cfg_path))


def setup_logging(level: int = logging.INFO):
    """ログレベルを引数で受け取り、StreamHandler だけを設定する"""
    logger = logging.getLogger()
    logger.setLevel(level)
    # 既存ハンドラをクリア
    logger.handlers.clear()

    # StreamHandler を設定
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(level)
    formatter = logging.Formatter("[%(levelname)s] %(name)s: %(message)s")
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)


def setup_serialosc(app) -> monome.SerialOsc:
    """
    SerialOsc インスタンスを生成し、Arc デバイスが追加された際に自動接続する
    コールバックを登録して返す。
    使い方
    async def main() -> None:
        loop = asyncio.get_running_loop()
        app = OperateArcApp()

        # SerialOsc をセットアップして接続
        serialosc = setup_serialosc(app)
        await serialosc.connect()

        # 無限待機（KeyboardInterrupt で終了）
        await loop.create_future()


    if __name__ == "__main__":
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            LOGGER.info("Exiting on keyboard interrupt.")
    """
    serialosc = monome.SerialOsc()

    def serialosc_device_added(dev_id: str, dev_type: str, port: int) -> None:
        if "arc" not in dev_type.lower():
            LOGGER.info("Ignore %s (%s) – not an Arc", dev_id, dev_type)
            return

        LOGGER.info("Connecting to %s (%s) on port %d", dev_id, dev_type, port)
        # ArcApp.arc は asyncio 対応なので task を発行して接続
        asyncio.create_task(app.arc.connect("127.0.0.1", port))

    serialosc.device_added_event.add_handler(serialosc_device_added)
    return serialosc
