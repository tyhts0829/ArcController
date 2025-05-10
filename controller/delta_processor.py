import logging

from enums.enums import ValueStyle
from model.model import RingState
from util.util import clamp

LOGGER = logging.getLogger(__name__)


class DeltaProcessor:
    """値の更新ロジックを担当するクラス"""

    def update_value(self, ring_state: RingState, delta: int) -> float:
        style = ring_state.value_style
        current_value = ring_state.current_value

        # --- スタイル別増分計算 ---------------------------------------
        if style in (ValueStyle.LINEAR, ValueStyle.BIPOLAR):
            new_val = current_value + delta
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
            new_val = round(new_val)  # 丸め
            new_val = max(0, min(127, new_val))  # saturate
        elif style == ValueStyle.MIDI_14BIT:
            new_val = round(new_val)  # 丸め
            new_val = max(0, min(16383, new_val))  # saturate

        return new_val

    def update_frequency(self, ring_state: RingState, delta: float) -> float:
        return clamp(ring_state.lfo_frequency + delta, 0.0, 1.0)
