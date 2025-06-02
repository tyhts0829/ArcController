#!/usr/bin/env python3
"""
control_sender.py のテスト
"""

import time

import asyncio
from unittest.mock import Mock, patch

import pytest

from arc.services.sender.control_sender import AiOscSender, MidiSender


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


class TestAiOscSender:
    """AiOscSender クラスのテスト"""

    def test_osc_sender_initialization(self):
        """AiOscSender の初期化テスト"""
        sender = AiOscSender(host="192.168.1.100", port=8000)
        assert sender.host == "192.168.1.100"
        assert sender.port == 8000
        assert sender.enabled is True
        assert sender._transport is None
        assert sender._protocol is None

    @pytest.mark.asyncio
    async def test_osc_sender_start_stop(self):
        """AiOscSender の開始・停止テスト"""
        sender = AiOscSender(host="127.0.0.1", port=8000)
        
        # 開始テスト
        with patch('arc.services.sender.control_sender.asyncio.get_running_loop') as mock_get_loop:
            mock_loop = Mock()
            mock_transport = Mock()
            mock_protocol = Mock()
            
            mock_get_loop.return_value = mock_loop
            mock_loop.create_datagram_endpoint = Mock(return_value=asyncio.coroutine(lambda: (mock_transport, mock_protocol))())
            
            result = await sender.start()
            assert result is True
            assert sender._transport is not None
            assert sender._protocol is not None
            
            # 停止テスト
            sender.stop()
            mock_transport.close.assert_called_once()

    def test_osc_sender_send_float(self):
        """OSC float送信テスト"""
        sender = AiOscSender()
        mock_protocol = Mock()
        sender._protocol = mock_protocol
        
        # float送信
        sender.send_float("/test/float", 0.75)
        mock_protocol.send.assert_called_once_with("/test/float", 0.75)

    def test_osc_sender_send_int(self):
        """OSC int送信テスト"""
        sender = AiOscSender()
        mock_protocol = Mock()
        sender._protocol = mock_protocol
        
        # int送信
        sender.send_int("/test/int", 42)
        mock_protocol.send.assert_called_once_with("/test/int", 42)

    def test_osc_sender_send_bundle(self):
        """OSC bundle送信テスト"""
        sender = AiOscSender()
        mock_protocol = Mock()
        sender._protocol = mock_protocol
        
        # bundle送信
        bundle = [("/foo", 1), ("/bar", 0.5), ("/baz", 100)]
        sender.send_bundle(bundle)
        
        # 各メッセージが送信されたことを確認
        assert mock_protocol.send.call_count == 3
        mock_protocol.send.assert_any_call("/foo", 1)
        mock_protocol.send.assert_any_call("/bar", 0.5)
        mock_protocol.send.assert_any_call("/baz", 100)

    def test_osc_sender_close(self):
        """OSC sender closeテスト"""
        sender = AiOscSender()
        mock_transport = Mock()
        sender._transport = mock_transport
        
        # close実行
        sender.close()
        mock_transport.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_osc_sender_start_when_disabled(self):
        """無効化されている場合のstart()テスト"""
        sender = AiOscSender(enabled=False)
        
        result = await sender.start()
        assert result is False
        assert sender._transport is None
        assert sender._protocol is None

    def test_osc_sender_send_when_disabled(self):
        """無効化されている場合の送信は無視されることを確認"""
        sender = AiOscSender(enabled=False)
        mock_protocol = Mock()
        sender._protocol = mock_protocol
        
        # 無効化されている場合、プロトコルがあっても送信されない
        sender.send_float("/test", 1.0)
        sender.send_int("/test", 42)
        sender.send_bundle([("/test", 1)])
        
        # 何も送信されていないことを確認
        mock_protocol.send.assert_not_called()


if __name__ == "__main__":
    # 単体でテストを実行
    pytest.main([__file__, "-v"])
