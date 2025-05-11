import logging
from types import SimpleNamespace

import pytest

from controller.delta_processor import DeltaProcessor
from enums.enums import ValueStyle

dp = DeltaProcessor()


# -----------------------------------------------------------------------------
# update_value() のテスト
# -----------------------------------------------------------------------------
@pytest.mark.parametrize(
    "style,start,delta,expected",
    [
        # ---------------------------------------------------------------------
        # LINEAR: 0.0‒1.0 にクランプ
        # ---------------------------------------------------------------------
        (ValueStyle.LINEAR, 0.5, 0.6, 1.0),  # 少し超え → 上限へ
        (ValueStyle.LINEAR, 0.5, -0.6, 0.0),  # 少し下回る → 下限へ
        (ValueStyle.LINEAR, 0.3, 0.2, 0.5),  # 範囲内
        (ValueStyle.LINEAR, 0.0, 9999, 1.0),  # 極端に大きいΔ → 上限
        (ValueStyle.LINEAR, 1.0, -9999, 0.0),  # 極端に小さいΔ → 下限
        # ---------------------------------------------------------------------
        # BIPOLAR: -0.5‒0.5 にクランプ
        # ---------------------------------------------------------------------
        (ValueStyle.BIPOLAR, 0.0, 0.6, 0.5),
        (ValueStyle.BIPOLAR, 0.0, -0.6, -0.5),
        (ValueStyle.BIPOLAR, 0.3, 0.1, 0.4),
        (ValueStyle.BIPOLAR, 0.5, 9999, 0.5),  # 上限を大幅に超える
        (ValueStyle.BIPOLAR, -0.5, -9999, -0.5),  # 下限を大幅に下回る
        # ---------------------------------------------------------------------
        # INFINITE: クランプなし
        # ---------------------------------------------------------------------
        (ValueStyle.INFINITE, 100, 50, 150),
        (ValueStyle.INFINITE, -100, -50, -150),
        (ValueStyle.INFINITE, 0, 9999, 9999),
        # ---------------------------------------------------------------------
        # MIDI 7bit: 0‒127 (int) にクランプ＋丸め
        # ---------------------------------------------------------------------
        (ValueStyle.MIDI_7BIT, 120, 10, 127),
        (ValueStyle.MIDI_7BIT, 3, -10, 0),
        (ValueStyle.MIDI_7BIT, 5.4, 0.4, 6),  # 5.8 → round → 6
        (ValueStyle.MIDI_7BIT, 0, 9999, 127),  # 上限
        (ValueStyle.MIDI_7BIT, 127, 9999, 127),  # 既に上限
        (ValueStyle.MIDI_7BIT, 127, -9999, 0),  # 下限
        # ---------------------------------------------------------------------
        # MIDI 14bit: 0‒16383 (int) にクランプ＋丸め
        # ---------------------------------------------------------------------
        (ValueStyle.MIDI_14BIT, 16300, 100, 16383),
        (ValueStyle.MIDI_14BIT, 50, -100, 0),
        (ValueStyle.MIDI_14BIT, 50.2, 0.3, 50),  # 50.5 → round → 50
        (ValueStyle.MIDI_14BIT, 0, 999999, 16383),  # 極端な上限
        (ValueStyle.MIDI_14BIT, 16383, 999999, 16383),
    ],
)
def test_update_value(style, start, delta, expected):
    """DeltaProcessor.update_value() が ValueStyle ごとに正しく丸め・クランプするか"""
    ring_state = SimpleNamespace(
        current_value=start,
        value_style=style,
    )
    result = dp.update_value(ring_state, delta)
    assert result == pytest.approx(expected)


def test_update_value_unknown_style(caplog):
    """
    未知の ValueStyle を指定したときにログが警告を出しつつ、値を更新しないことを確認。
    """
    ring_state = SimpleNamespace(current_value=0.5, value_style="UNKNOWN_STYLE")  # 本来の列挙型に存在しない文字列
    with caplog.at_level(logging.WARNING):
        result = dp.update_value(ring_state, 0.1)
        # ログの内容確認
        assert any("Unknown ValueStyle" in msg for msg in caplog.text.splitlines())
    # 値は変化しない
    assert result == pytest.approx(0.5)


# -----------------------------------------------------------------------------
# update_frequency() のテスト
# -----------------------------------------------------------------------------
@pytest.mark.parametrize(
    "start,delta,expected",
    [
        (0.5, 0.6, 1.0),  # 上限クランプ
        (0.3, -0.5, 0.0),  # 下限クランプ
        (0.2, 0.3, 0.5),  # 範囲内
        (0.0, 9999, 1.0),  # 大きな正値
        (1.0, -9999, 0.0),  # 大きな負値
    ],
)
def test_update_frequency(start, delta, expected):
    """DeltaProcessor.update_frequency() が 0.0‒1.0 にクランプするか"""
    ring_state = SimpleNamespace(lfo_frequency=start)
    result = dp.update_frequency(ring_state, delta)
    assert result == pytest.approx(expected)
