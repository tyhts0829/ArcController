"""
controller.delta_processor
--------------------------

リング値や LFO 周波数をエンコーダ Δ から更新するユーティリティ。
"""

import logging

from enums.enums import ValueStyle
from model.model import RingState
from util.util import clamp

LOGGER = logging.getLogger(__name__)


class DeltaProcessor:
    """
    値の更新ロジックを担当するクラス。

    Args:
        None
    """

    def update_value(self, ring_state: RingState, delta: int) -> float | int:
        """リングの現在値をスタイルに応じて更新する。

        Args:
            ring_state (RingState): 更新対象のリング状態。
            delta (int): 入力エンコーダの増分。

        Returns:
            float: 更新後の値。
        """
        style = ring_state.value_style
        new_val = ring_state.current_value + delta

        # --- スタイル別の丸め・制限 -------------------------------
        if style == ValueStyle.LINEAR:
            new_val = clamp(new_val, 0.0, 1.0)
        elif style == ValueStyle.BIPOLAR:
            new_val = clamp(new_val, -0.5, 0.5)
        elif style == ValueStyle.INFINITE:
            # 無限レンジはそのまま返す
            pass
        elif style == ValueStyle.MIDI_7BIT:
            new_val = clamp(round(new_val), 0, 127)
        elif style == ValueStyle.MIDI_14BIT:
            new_val = clamp(round(new_val), 0, 16383)
        else:
            LOGGER.warning("Unknown ValueStyle %s – no update", style)
            return ring_state.current_value

        return new_val

    def update_frequency(self, ring_state: RingState, delta: float) -> float:
        """LFO 周波数を 0.0‒1.0 範囲で更新する。

        Args:
            ring_state (RingState): 更新対象のリング状態。
            delta (float): 入力エンコーダの増分。

        Returns:
            float: 更新後の LFO 周波数 (0.0‒1.0)。
        """
        return clamp(ring_state.lfo_frequency + delta, 0.0, 1.0)
