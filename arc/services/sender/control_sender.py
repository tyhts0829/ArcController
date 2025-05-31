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

    Examples:
        >>> from services.sender.control_sender import MidiSender
        >>> midi = MidiSender()                  # "ArcController OUT" という仮想ポートが作成される
        >>> midi.send_cc_7bit(20, 64)            # CC #20, 値 64 (0x40) を送信
        >>> midi.send_cc_14bit(21, 8192)         # CC #21 (MSB/LSB) に 14‑bit 値 0x2000 を送信
    """

    def __init__(self, port_name: str = "ArcController OUT") -> None:
        self.port_name = port_name
        self.port = None
        self.thread = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def start(self):
        """MIDI送信を開始"""
        try:
            mido.set_backend("mido.backends.rtmidi")
            self.port = mido.open_output(self.port_name, virtual=True)  # type: ignore
            LOGGER.info("MIDI 送信ポート '%s' を作成", self.port_name)
            return True
        except Exception as e:
            LOGGER.error("MIDI 送信ポートの作成に失敗: %s", e)
            return False

    def stop(self):
        """MIDI送信を停止"""
        if self.thread:
            self.thread.join()
        if self.port:
            self.port.close()
            LOGGER.info("MIDI 送信ポートを閉じました")

    def send_cc_7bit(self, cc_num: int, value: float, channel: int = 0) -> None:
        """7‑bit Control‑Change を送信する。"""
        value = int(clamp(value * 127, 0, 127))
        LOGGER.debug("MIDI 7‑bit CC → ch=%d cc=%d value=%d", channel, cc_num, value)
        msg = mido.Message("control_change", channel=channel, control=cc_num, value=value)
        self.port.send(msg)  # type: ignore

    def send_cc_14bit(self, cc_num: int, value: float, channel: int = 0) -> None:
        """14‑bit Control‑Change を MSB/LSB のペアで送信する。

        *MSB* = ``cc_num``, *LSB* = ``cc_num + 32`` という MIDI 1.0 の標準に従う。
        """
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
class _AioOscProtocol(aiosc.OSCProtocol):
    """受信ハンドラ無し・送り専用のプロトコル。"""

    pass


class AioOscSender:
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
            lambda: _AioOscProtocol(),
            local_addr=("0.0.0.0", 0),  # OS にポート番号を任せる
            remote_addr=(host, port),
        )
        transport, protocol = loop.run_until_complete(coro)
        self._transport: asyncio.DatagramTransport = transport
        self._protocol: _AioOscProtocol = protocol  # type: ignore

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
