"""
controller.preset_manager
-------------------------

プリセット切り替えロジックを担当するモジュール。
"""

import logging
import math
from typing import List

from model.model import RingState

LOGGER = logging.getLogger(__name__)


class PresetManager:
    """リングごとのプリセット切り替え状態を管理するクラス。

    Args:
        presets (List[dict]): 利用可能なプリセット定義。
        threshold (int): 1 ステップとして扱う累積 Δ のしきい値。
        num_rings (int): 管理対象リング数。
    """

    def __init__(self, presets: List[dict], threshold: int, num_rings: int) -> None:
        self.presets = presets
        self.threshold = threshold
        # リングごとに累積 Δ を保持
        self._acc_delta: dict[int, int] = {i: 0 for i in range(num_rings)}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def process_delta(self, ring_idx: int, delta: int, ring_state: RingState) -> bool:
        """Δ を累積ししきい値を超えた回数だけプリセットを循環させる。

        Args:
            ring_idx (int): リングインデックス。
            delta (int): 今回の増分 Δ。
            ring_state (RingState): 対象リングの状態。

        Returns:
            bool: プリセットが変更されたとき True。
        """
        acc = self._acc_delta[ring_idx] + delta
        steps = math.trunc(acc / self.threshold)
        # 残余を保持
        self._acc_delta[ring_idx] = acc - steps * self.threshold

        LOGGER.debug(
            "PresetManager: ring=%d Δ=%+d acc=%d steps=%d residual=%d",
            ring_idx,
            delta,
            acc,
            steps,
            self._acc_delta[ring_idx],
        )

        if steps == 0:
            return False

        num_presets = len(self.presets)
        ring_state.preset_index = (ring_state.preset_index + steps) % num_presets
        ring_state.apply_preset(self.presets[ring_state.preset_index])
        return True

    def reset(self) -> None:
        """すべてのリングの累積 Δ をリセットする。"""
        for k in self._acc_delta:
            self._acc_delta[k] = 0
