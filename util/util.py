"""
util.util
---------

文字列フォーマット、範囲クランプ、YAML 読み込み、ロギング設定、SerialOsc セットアップなど
Arc アプリ全体で共有されるユーティリティ関数群。
"""

import asyncio
import logging
from pathlib import Path

from omegaconf import OmegaConf

import monome

LOGGER = logging.getLogger(__name__)


def fmt(v) -> str:
    """数値を文字列へフォーマットするヘルパ。

    Args:
        v (Any): 整形対象。`float` の場合は小数 3 桁へ丸める。

    Returns:
        str: 整形後の文字列。
    """
    return f"{v:.3f}" if isinstance(v, float) else str(v)


def clamp(x: float, lo: float, hi: float) -> float:
    """値を指定範囲へクランプする。

    Args:
        x (float): 入力値。
        lo (float): 下限。
        hi (float): 上限。

    Returns:
        float: クランプされた値。
    """
    return max(lo, min(hi, x))


def config_loader(cfg_path: Path = Path("config/config.yaml")) -> OmegaConf:
    """YAML 設定ファイルを読み込み `OmegaConf` オブジェクトを返す。

    Args:
        cfg_path (Path, optional): YAML ファイルのパス。デフォルトは
            `config/config.yaml`。

    Returns:
        OmegaConf: 読み込まれた DictConfig。
    """
    return OmegaConf.load(str(cfg_path))


def setup_logging(level: int = logging.INFO):
    """ルートロガーに `StreamHandler` を設定する。

    Args:
        level (int, optional): ログレベル。デフォルトは `logging.INFO`。
    """
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
    """Arc デバイス検出時に自動接続する `SerialOsc` を生成する。

    Args:
        app (monome.ArcApp): 接続対象の ArcApp インスタンス。

    Returns:
        monome.SerialOsc: 準備済みの `SerialOsc` インスタンス。
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
