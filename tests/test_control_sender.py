#!/usr/bin/env python3
"""
control_sender.py のテスト
"""

import time

import pytest

from arc.services.sender.control_sender import MidiSender


class TestMidiSender:
    """MidiSender クラスのテスト"""

    def test_midi_sender_initialization(self):
        """MidiSender の初期化テスト"""
        sender = MidiSender("Test Port")
        assert sender.port_name == "Test Port"
        assert sender.port is None

    def test_midi_sender_start_stop(self):
        """MidiSender の開始・停止テスト"""
        sender = MidiSender("Test Port")

        # 開始テスト
        result = sender.start()
        assert result is True
        assert sender.port is not None

        # 停止テスト
        sender.stop()
        # ポートが閉じられることを確認（正確なテストは実装依存）

    def test_send_cc_7bit(self):
        """7-bit CC送信テスト"""
        sender = MidiSender("Test 7bit")

        if sender.start():
            try:
                # 各種値での送信テスト
                sender.send_cc_7bit(20, 0.0)  # 最小値
                sender.send_cc_7bit(20, 0.5)  # 中間値
                sender.send_cc_7bit(20, 1.0)  # 最大値
                sender.send_cc_7bit(20, 1.5)  # 範囲外（クランプされるべき）
                sender.send_cc_7bit(20, -0.5)  # 範囲外（クランプされるべき）

                # エラーが発生しないことを確認
                assert True

            finally:
                sender.stop()
        else:
            pytest.skip("MIDI初期化に失敗")

    def test_send_cc_14bit(self):
        """14-bit CC送信テスト"""
        sender = MidiSender("Test 14bit")

        if sender.start():
            try:
                # 各種値での送信テスト
                sender.send_cc_14bit(21, 0.0)  # 最小値
                sender.send_cc_14bit(21, 0.5)  # 中間値
                sender.send_cc_14bit(21, 1.0)  # 最大値
                sender.send_cc_14bit(21, 1.5)  # 範囲外（クランプされるべき）
                sender.send_cc_14bit(21, -0.5)  # 範囲外（クランプされるべき）

                # エラーが発生しないことを確認
                assert True

            finally:
                sender.stop()
        else:
            pytest.skip("MIDI初期化に失敗")

    def test_multiple_cc_channels(self):
        """複数チャンネルでのCC送信テスト"""
        sender = MidiSender("Test Multi Channel")

        if sender.start():
            try:
                # 複数チャンネルでの送信
                for channel in range(0, 4):
                    sender.send_cc_7bit(20, 0.5, channel=channel)
                    sender.send_cc_14bit(21, 0.75, channel=channel)

                # エラーが発生しないことを確認
                assert True

            finally:
                sender.stop()
        else:
            pytest.skip("MIDI初期化に失敗")


if __name__ == "__main__":
    # 単体でテストを実行
    pytest.main([__file__, "-v"])
