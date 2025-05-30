"""
mode.disconnect_mode
--------------------

`DisconnectMode` は Arc デバイスが切断された際に呼び出されるクリーンアップ専用モード。

主な責務:
* LFO エンジンの停止を安全に（asyncio タスクとして）実行する
* それ以外の入力イベントはすべて無視し、副作用を発生させない

公開 API は ``DisconnectMode`` クラスのみ。
"""

from __future__ import annotations

import asyncio

import monome

from arc.modes.base_mode import BaseMode
from arc.services.lfo.lfo_engine import LFOEngine


class DisconnectMode(BaseMode):
    """Arc デバイス切断時のクリーンアップ処理を担当するモード。

    Args:
        lfo_engine (LfoEngine): LED アニメーションを制御しているエンジン。
            デバイス切断時に安全に停止させる。
    """

    def __init__(self, lfo_engine: LFOEngine) -> None:
        """依存オブジェクトを保持するだけで特別な初期化は行わない。"""
        self._lfo_engine = lfo_engine

    def on_arc_ready(self, arc: monome.Arc) -> None:
        """DisconnectMode では Arc 接続イベントを無視する。

        Args:
            arc (monome.Arc): 接続された Arc デバイス。
        """
        pass

    def on_arc_disconnect(self) -> None:
        """Arc デバイス切断時に LFO エンジンの停止を非同期でスケジュールする。"""
        # stop() は async になったためタスクとして実行
        asyncio.create_task(self._lfo_engine.stop())

    def on_arc_delta(self, ring_idx: int, delta: int) -> None:
        """リングの回転イベントは DisconnectMode では無視する。"""
        pass

    def on_arc_key(self, x: int, pressed: bool) -> None:
        """キー押下／離上イベントは DisconnectMode では無視する。"""
        pass
