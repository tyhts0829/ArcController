import logging

from enums.enums import ValueStyle
from model.model import RingState

LOGGER = logging.getLogger("ValueProcessor")


class ValueProcessor:
    """値の更新ロジックを担当するクラス"""

    speed = 0.001  # ring_deltaに対するvalueの加算速度

    def update(self, ring_state: RingState, delta: int) -> float:
        style = ring_state.value_style
        current_value = ring_state.current_value

        # --- スタイル別増分計算 ---------------------------------------
        if style in (ValueStyle.LINEAR, ValueStyle.BIPOLAR):
            inc = delta * self.speed
            new_val = current_value + inc
        elif style == ValueStyle.INFINITE:
            new_val = current_value + delta  # そのまま加算
        elif style in (ValueStyle.MIDI_7BIT, ValueStyle.MIDI_14BIT):
            new_val = current_value + delta
        else:
            LOGGER.warning("Unknown ValueStyle %s – no update", style)
            return current_value

        # --- 範囲制約 ---------------------------------------------------
        if style == ValueStyle.LINEAR:
            new_val = max(0.0, min(1.0, new_val))
        elif style == ValueStyle.BIPOLAR:
            new_val = max(-0.5, min(0.5, new_val))
        elif style == ValueStyle.MIDI_7BIT:
            new_val = max(0, min(127, int(new_val)))
        elif style == ValueStyle.MIDI_14BIT:
            new_val = max(0, min(16383, int(new_val)))

        return new_val
