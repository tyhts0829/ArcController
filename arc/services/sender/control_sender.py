"""
midi_sender
-----------
仮想ポートを自動生成して MIDI CC を送出するユーティリティ。

- 7‑bit CC : ``send_cc_7bit()``
- 14‑bit CC: ``send_cc_14bit()``
- OSC 送信 : ``AioOscSender``
"""

import asyncio
import logging
from typing import Any

import aiosc  # type: ignore
import mido

from arc.utils.util import clamp

LOGGER = logging.getLogger(__name__)


class MidiSender:
    """MIDI CC 送信ラッパー。

    引数に指定した名前で **仮想 MIDI‑OUT ポート** を自動生成し、
    `send_cc_7bit()` ／ `send_cc_14bit()` で任意の CC メッセージを送信できる。

    Args:
        port_name (str): 作成する仮想ポート名。
        channel (int): MIDIチャンネル (1-16)。内部では0-15に変換して使用。
        enabled (bool): MIDI送信を有効にするかどうか。

    """

    def __init__(self, port_name: str, channel: int = 1, enabled: bool = True) -> None:
        self.port_name = port_name
        # MIDIチャンネル: ユーザー向け表記(1-16) → プロトコル値(0-15)に変換
        # 音楽ソフトでは「チャンネル1」と表示されるが、MIDI規格では内部的に0を使用
        self.channel = max(0, min(15, channel - 1))
        self.enabled = enabled
        self.port = None
        self.thread = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def start(self) -> bool:
        """MIDI送信を開始"""
        if not self.enabled:
            LOGGER.info("MIDI 送信は無効化されています")
            return False
        try:
            mido.set_backend("mido.backends.rtmidi")
            self.port = mido.open_output(self.port_name, virtual=True)  # type: ignore
            LOGGER.info("MIDI 送信ポート '%s' を作成", self.port_name)
            return True
        except Exception as e:
            LOGGER.error("MIDI 送信ポートの作成に失敗: %s", e)
            return False

    def stop(self) -> None:
        """MIDI送信を停止"""
        if not self.enabled:
            return
        if self.thread:
            self.thread.join()
        if self.port:
            self.port.close()
            self.port = None
            LOGGER.info("MIDI 送信ポートを閉じました")

    def send_cc_7bit(self, cc_num: int, value: float, channel: int | None = None) -> None:
        """7‑bit Control‑Change を送信する。"""
        if not self.enabled or self.port is None:
            return
        if channel is None:
            channel = self.channel
        value = int(clamp(value * 127, 0, 127))
        LOGGER.debug("MIDI 7‑bit CC → ch=%d cc=%d value=%d", channel, cc_num, value)
        msg = mido.Message("control_change", channel=channel, control=cc_num, value=value)
        self.port.send(msg)  # type: ignore

    def send_cc_14bit(self, cc_num: int, value: float, channel: int | None = None) -> None:
        """14‑bit Control‑Change を MSB/LSB のペアで送信する。

        *MSB* = ``cc_num``, *LSB* = ``cc_num + 32`` という MIDI 1.0 の標準に従う。
        """
        if not self.enabled or self.port is None:
            return
        if channel is None:
            channel = self.channel
        value = int(clamp(value * 16383, 0, 16383))
        msb = (value >> 7) & 0x7F
        lsb = value & 0x7F
        LOGGER.debug(
            "MIDI 14‑bit CC → ch=%d cc=%d value=%d (MSB=%d LSB=%d)",
            channel,
            cc_num,
            value,
            msb,
            lsb,
        )
        msg_msb = mido.Message("control_change", channel=channel, control=cc_num, value=msb)
        msg_lsb = mido.Message("control_change", channel=channel, control=cc_num + 32, value=lsb)
        self.port.send(msg_msb)  # type: ignore
        self.port.send(msg_lsb)  # type: ignore


# ----------------------------------------------------------------------
# OSC Sender (aiosc ベース)
# ----------------------------------------------------------------------
class _AiOscProtocol(aiosc.OSCProtocol):
    """受信ハンドラ無し・送り専用のプロトコル。"""

    pass


class AiOscSender:
    """aiosc を用いた軽量 OSC 送信クライアント。

    引数で指定した ``host`` / ``port`` へ **非同期ループ共有** で
    任意の OSC メッセージを送信できる。同期メソッドなので
    `asyncio.sleep()` 等と組み合わせてもブロッキングが起きにくい。

    Args:
        host (str): 送信先ホスト。デフォルト ``127.0.0.1``。
        port (int): 送信先ポート。デフォルト ``57120``。
        loop (asyncio.AbstractEventLoop | None): 共有したいイベントループ。

    Examples:
        >>> from services.sender.control_sender import AioOscSender
        >>> osc = AioOscSender(port=57121)          # TouchDesigner などのポートに合わせる
        >>> osc.send_float("/arc/ring/0", 0.42)     # float 値を送信
        >>> osc.send_int("/arc/ring/1", 64)         # int 値を送信
        >>> osc.send_bundle([("/foo", 1), ("/bar", 0.5)])  # バッチ送信
        >>> osc.close()                             # 明示的にソケットを閉じる
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 57120,
        loop: asyncio.AbstractEventLoop | None = None,
    ) -> None:
        if loop is None:
            loop = asyncio.get_event_loop()

        # 送信専用エンドポイントを作成
        coro = loop.create_datagram_endpoint(
            lambda: _AiOscProtocol(),
            local_addr=("0.0.0.0", 0),  # OS にポート番号を任せる
            remote_addr=(host, port),
        )
        transport, protocol = loop.run_until_complete(coro)
        self._transport: asyncio.DatagramTransport = transport
        self._protocol: _AiOscProtocol = protocol  # type: ignore

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def send_float(self, address: str, value: float) -> None:
        """OSC アドレスへ float 値を送信する。"""
        self._protocol.send(address, float(value))

    def send_int(self, address: str, value: int) -> None:
        """OSC アドレスへ int 値を送信する。"""
        self._protocol.send(address, int(value))

    def send_bundle(self, bundle: list[tuple[str, Any]]) -> None:
        """複数メッセージをまとめて送信するユーティリティ。

        Args:
            bundle: (address, value) のペア列。
        """
        for addr, val in bundle:
            self._protocol.send(addr, val)

    def close(self) -> None:
        """ソケットを閉じてリソースを解放する。"""
        self._transport.close()
