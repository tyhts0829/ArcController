"""
mode.base_mode
--------------

すべてのモードクラスが実装すべきコールバックインターフェースを定義する抽象基底クラス
(:class:`BaseMode`) を提供するモジュール。

monome Arc デバイスからの入力イベントごとに 4 つのメソッド
(:py:meth:`on_arc_ready`, :py:meth:`on_arc_disconnect`,
:py:meth:`on_arc_delta`, :py:meth:`on_arc_key`) を定義し、
状態を持たないピュアインターフェースとしている。
"""

from abc import ABC, abstractmethod

import monome


class BaseMode(ABC):
    """Arc 入力イベント用の共通インターフェース。

    サブクラスは以下 4 つの抽象メソッドを実装すること:

    * on_arc_ready(arc): デバイス接続時
    * on_arc_disconnect(): デバイス切断時
    * on_arc_delta(ring_idx, delta): エンコーダ回転
    * on_arc_key(x, pressed): キー押下／離上
    """

    @abstractmethod
    def on_arc_ready(self, arc: monome.Arc) -> None:
        """Arc デバイス接続完了時に呼び出されるフック。

        Args:
            arc (monome.Arc): 接続された Arc デバイス。
        """
        pass

    @abstractmethod
    def on_arc_disconnect(self) -> None:
        """Arc デバイス切断時に呼び出されるフック。"""
        pass

    @abstractmethod
    def on_arc_delta(self, ring_idx: int, delta: int) -> None:
        """リングの回転入力を受け取るフック。

        Args:
            ring_idx (int): 回転したリング番号 (0‒3)。
            delta (int): 回転量。時計回りが正、反時計回りが負。
        """
        pass

    @abstractmethod
    def on_arc_key(self, x: int, pressed: bool) -> None:
        """キー押下／離上入力を受け取るフック。

        Args:
            x (int): キー番号。
            pressed (bool): 押下時 True、離上時 False。
        """
        pass
