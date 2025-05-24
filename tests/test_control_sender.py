"""
test_control_sender
------------------
MidiSender クラスの単体テスト。

Tests:
* MidiSender.__init__ - 仮想ポート作成とフォールバック
* MidiSender.send_cc_7bit - 7-bit CC メッセージ送信
* MidiSender.send_cc_14bit - 14-bit CC メッセージ送信（MSB/LSB ペア）
"""

from unittest.mock import Mock, patch

import pytest

from src.services.sender.control_sender import MidiSender


# ----------------------------------------------------------------------
# MidiSender.__init__ テスト
# ----------------------------------------------------------------------
@patch("src.services.sender.control_sender.rtmidi.MidiOut")
def test_midi_sender_init_virtual_port_success(mock_midi_out_class):
    """仮想ポートの作成が成功する場合のテスト"""
    mock_midi_out = Mock()
    mock_midi_out_class.return_value = mock_midi_out

    midi_sender = MidiSender("TestPort")

    mock_midi_out_class.assert_called_once()
    mock_midi_out.open_virtual_port.assert_called_once_with("TestPort")
    assert midi_sender._midi_out == mock_midi_out


@patch("src.services.sender.control_sender.rtmidi.MidiOut")
def test_midi_sender_init_default_port_name(mock_midi_out_class):
    """デフォルトのポート名が使用される場合のテスト"""
    mock_midi_out = Mock()
    mock_midi_out_class.return_value = mock_midi_out

    midi_sender = MidiSender()

    mock_midi_out.open_virtual_port.assert_called_once_with("ArcController OUT")


@patch("src.services.sender.control_sender.rtmidi.MidiOut")
def test_midi_sender_init_fallback_to_existing_port(mock_midi_out_class):
    """仮想ポート作成失敗時に既存ポートにフォールバックする場合のテスト"""
    mock_midi_out = Mock()
    mock_midi_out_class.return_value = mock_midi_out

    # 仮想ポート作成は失敗するが、既存ポートは存在する
    mock_midi_out.open_virtual_port.side_effect = RuntimeError("Virtual port failed")
    mock_midi_out.get_ports.return_value = ["Port 0", "Port 1"]

    midi_sender = MidiSender("TestPort")

    mock_midi_out.open_virtual_port.assert_called_once_with("TestPort")
    mock_midi_out.get_ports.assert_called_once()
    mock_midi_out.open_port.assert_called_once_with(0)


@patch("src.services.sender.control_sender.rtmidi.MidiOut")
def test_midi_sender_init_no_fallback_ports(mock_midi_out_class):
    """仮想ポート作成失敗かつ既存ポートもない場合のテスト"""
    mock_midi_out = Mock()
    mock_midi_out_class.return_value = mock_midi_out

    # 仮想ポート作成は失敗し、既存ポートも存在しない
    mock_midi_out.open_virtual_port.side_effect = RuntimeError("Virtual port failed")
    mock_midi_out.get_ports.return_value = []

    midi_sender = MidiSender("TestPort")

    mock_midi_out.open_virtual_port.assert_called_once_with("TestPort")
    mock_midi_out.get_ports.assert_called_once()
    mock_midi_out.open_port.assert_not_called()


# ----------------------------------------------------------------------
# MidiSender.send_cc_7bit テスト
# ----------------------------------------------------------------------
@patch("src.services.sender.control_sender.rtmidi.MidiOut")
def test_send_cc_7bit_basic(mock_midi_out_class):
    """7-bit CC の基本的な送信テスト"""
    mock_midi_out = Mock()
    mock_midi_out_class.return_value = mock_midi_out

    midi_sender = MidiSender()
    midi_sender.send_cc_7bit(cc_num=20, value=0.5, channel=0)

    # value=0.5 -> int(0.5 * 127) = 63
    expected_message = [0xB0, 20, 63]
    mock_midi_out.send_message.assert_called_once_with(expected_message)


@patch("src.services.sender.control_sender.rtmidi.MidiOut")
def test_send_cc_7bit_boundary_values(mock_midi_out_class):
    """7-bit CC の境界値テスト"""
    mock_midi_out = Mock()
    mock_midi_out_class.return_value = mock_midi_out

    midi_sender = MidiSender()

    # 最小値: 0.0 -> 0
    midi_sender.send_cc_7bit(cc_num=1, value=0.0)
    mock_midi_out.send_message.assert_called_with([0xB0, 1, 0])

    # 最大値: 1.0 -> 127
    midi_sender.send_cc_7bit(cc_num=2, value=1.0)
    mock_midi_out.send_message.assert_called_with([0xB0, 2, 127])

    # 範囲外（負の値）: -0.5 -> 0（クランプ）
    midi_sender.send_cc_7bit(cc_num=3, value=-0.5)
    mock_midi_out.send_message.assert_called_with([0xB0, 3, 0])

    # 範囲外（1.0超過）: 1.5 -> 127（クランプ）
    midi_sender.send_cc_7bit(cc_num=4, value=1.5)
    mock_midi_out.send_message.assert_called_with([0xB0, 4, 127])


@patch("src.services.sender.control_sender.rtmidi.MidiOut")
def test_send_cc_7bit_different_channels(mock_midi_out_class):
    """7-bit CC の異なるチャンネルでの送信テスト"""
    mock_midi_out = Mock()
    mock_midi_out_class.return_value = mock_midi_out

    midi_sender = MidiSender()

    # チャンネル 0
    midi_sender.send_cc_7bit(cc_num=10, value=0.25, channel=0)
    mock_midi_out.send_message.assert_called_with([0xB0, 10, 31])  # 0.25 * 127 = 31.75 -> 31

    # チャンネル 5
    midi_sender.send_cc_7bit(cc_num=11, value=0.75, channel=5)
    mock_midi_out.send_message.assert_called_with([0xB5, 11, 95])  # 0.75 * 127 = 95.25 -> 95


# ----------------------------------------------------------------------
# MidiSender.send_cc_14bit テスト
# ----------------------------------------------------------------------
@patch("src.services.sender.control_sender.rtmidi.MidiOut")
def test_send_cc_14bit_basic(mock_midi_out_class):
    """14-bit CC の基本的な送信テスト"""
    mock_midi_out = Mock()
    mock_midi_out_class.return_value = mock_midi_out

    midi_sender = MidiSender()
    midi_sender.send_cc_14bit(cc_num=20, value=0.5, channel=0)

    # value=0.5 -> int(0.5 * 16383) = 8191
    # MSB = (8191 >> 7) & 0x7F = 63
    # LSB = 8191 & 0x7F = 127
    expected_calls = [
        ([0xB0, 20, 63],),  # MSB
        ([0xB0, 52, 127],),  # LSB (cc_num + 32)
    ]

    actual_calls = mock_midi_out.send_message.call_args_list
    assert len(actual_calls) == 2
    assert actual_calls[0][0] == expected_calls[0]
    assert actual_calls[1][0] == expected_calls[1]


@patch("src.services.sender.control_sender.rtmidi.MidiOut")
def test_send_cc_14bit_boundary_values(mock_midi_out_class):
    """14-bit CC の境界値テスト"""
    mock_midi_out = Mock()
    mock_midi_out_class.return_value = mock_midi_out

    midi_sender = MidiSender()

    # 最小値: 0.0 -> 0 -> MSB=0, LSB=0
    midi_sender.send_cc_14bit(cc_num=1, value=0.0)
    calls = mock_midi_out.send_message.call_args_list[-2:]  # 最後の2回の呼び出し
    assert calls[0][0][0] == [0xB0, 1, 0]  # MSB
    assert calls[1][0][0] == [0xB0, 33, 0]  # LSB

    # 最大値: 1.0 -> 16383 -> MSB=127, LSB=127
    midi_sender.send_cc_14bit(cc_num=2, value=1.0)
    calls = mock_midi_out.send_message.call_args_list[-2:]
    assert calls[0][0][0] == [0xB0, 2, 127]  # MSB
    assert calls[1][0][0] == [0xB0, 34, 127]  # LSB


@patch("src.services.sender.control_sender.rtmidi.MidiOut")
def test_send_cc_14bit_clamping(mock_midi_out_class):
    """14-bit CC のクランプ処理テスト"""
    mock_midi_out = Mock()
    mock_midi_out_class.return_value = mock_midi_out

    midi_sender = MidiSender()

    # 範囲外（負の値）: -0.5 -> 0（クランプ）
    midi_sender.send_cc_14bit(cc_num=3, value=-0.5)
    calls = mock_midi_out.send_message.call_args_list[-2:]
    assert calls[0][0][0] == [0xB0, 3, 0]  # MSB
    assert calls[1][0][0] == [0xB0, 35, 0]  # LSB

    # 範囲外（1.0超過）: 1.5 -> 16383（クランプ）
    midi_sender.send_cc_14bit(cc_num=4, value=1.5)
    calls = mock_midi_out.send_message.call_args_list[-2:]
    assert calls[0][0][0] == [0xB0, 4, 127]  # MSB
    assert calls[1][0][0] == [0xB0, 36, 127]  # LSB


@patch("src.services.sender.control_sender.rtmidi.MidiOut")
def test_send_cc_14bit_different_channels(mock_midi_out_class):
    """14-bit CC の異なるチャンネルでの送信テスト"""
    mock_midi_out = Mock()
    mock_midi_out_class.return_value = mock_midi_out

    midi_sender = MidiSender()

    # チャンネル 0
    midi_sender.send_cc_14bit(cc_num=10, value=0.25, channel=0)
    calls = mock_midi_out.send_message.call_args_list[-2:]
    # 0.25 * 16383 = 4095.75 -> 4095
    # MSB = (4095 >> 7) & 0x7F = 31
    # LSB = 4095 & 0x7F = 127
    assert calls[0][0][0] == [0xB0, 10, 31]  # MSB
    assert calls[1][0][0] == [0xB0, 42, 127]  # LSB

    # チャンネル 5
    midi_sender.send_cc_14bit(cc_num=11, value=0.75, channel=5)
    calls = mock_midi_out.send_message.call_args_list[-2:]
    # 0.75 * 16383 = 12287.25 -> 12287
    # MSB = (12287 >> 7) & 0x7F = 95
    # LSB = 12287 & 0x7F = 127
    assert calls[0][0][0] == [0xB5, 11, 95]  # MSB
    assert calls[1][0][0] == [0xB5, 43, 127]  # LSB


# ----------------------------------------------------------------------
# パラメータ化テスト
# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    "value,expected_7bit,expected_14bit_msb,expected_14bit_lsb",
    [
        (0.0, 0, 0, 0),
        (0.1, 12, 12, 102),  # 0.1 * 127 = 12.7 -> 12; 0.1 * 16383 = 1638.3 -> 1638 -> MSB=12, LSB=102
        (0.25, 31, 31, 127),  # 0.25 * 127 = 31.75 -> 31; 0.25 * 16383 = 4095.75 -> 4095 -> MSB=31, LSB=127
        (0.5, 63, 63, 127),  # 0.5 * 127 = 63.5 -> 63; 0.5 * 16383 = 8191.5 -> 8191 -> MSB=63, LSB=127
        (0.75, 95, 95, 127),  # 0.75 * 127 = 95.25 -> 95; 0.75 * 16383 = 12287.25 -> 12287 -> MSB=95, LSB=127
        (1.0, 127, 127, 127),
    ],
)
@patch("src.services.sender.control_sender.rtmidi.MidiOut")
def test_cc_value_conversion_parametrized(
    mock_midi_out_class, value, expected_7bit, expected_14bit_msb, expected_14bit_lsb
):
    """様々な値に対する CC 変換の正確性をテスト"""
    mock_midi_out = Mock()
    mock_midi_out_class.return_value = mock_midi_out

    midi_sender = MidiSender()

    # 7-bit テスト
    midi_sender.send_cc_7bit(cc_num=1, value=value)
    mock_midi_out.send_message.assert_called_with([0xB0, 1, expected_7bit])

    # 14-bit テスト（値を再計算）
    value_14bit = int(value * 16383) if value <= 1.0 else 16383
    expected_msb = (value_14bit >> 7) & 0x7F
    expected_lsb = value_14bit & 0x7F

    midi_sender.send_cc_14bit(cc_num=2, value=value)
    calls = mock_midi_out.send_message.call_args_list[-2:]
    assert calls[0][0][0] == [0xB0, 2, expected_msb]  # MSB
    assert calls[1][0][0] == [0xB0, 34, expected_lsb]  # LSB
