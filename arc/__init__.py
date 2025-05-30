"""
ArcController パッケージ

このパッケージは、Monome Arcデバイス用のMIDIコントローラーアプリケーションを提供します。
"""

import multiprocessing
import time
from typing import Optional

# パッケージの主要な機能をインポートして公開
from arc.app import main, run

# パッケージのバージョン（必要に応じて）
__version__ = "1.0.0"

# プロセス管理用のグローバル変数
_arc_process: Optional[multiprocessing.Process] = None


def start() -> bool:
    """ArcControllerをバックグラウンドで非同期実行を開始します。

    Returns:
        bool: 正常に開始できた場合True、既に実行中または開始に失敗した場合False
    """
    global _arc_process

    if _arc_process is not None and _arc_process.is_alive():
        return False  # 既に実行中

    _arc_process = multiprocessing.Process(target=run)
    _arc_process.start()
    time.sleep(2)  # ArcControllerがMIDIポートを作成する時間を確保

    return _arc_process.is_alive()


def stop() -> bool:
    """実行中のArcControllerを停止します。

    Returns:
        bool: 正常に停止できた場合True、実行中でない場合False
    """
    global _arc_process

    if _arc_process is None or not _arc_process.is_alive():
        return False  # 実行中でない

    _arc_process.terminate()
    _arc_process.join(timeout=5)  # 最大5秒待機

    if _arc_process.is_alive():
        _arc_process.kill()  # 強制終了
        _arc_process.join()

    _arc_process = None
    return True


def is_running() -> bool:
    """ArcControllerが実行中かどうかを確認します。

    Returns:
        bool: 実行中の場合True、そうでなければFalse
    """
    global _arc_process
    return _arc_process is not None and _arc_process.is_alive()


# 公開するAPIを明示的に定義
__all__ = ["main", "run", "start", "stop", "is_running"]
