"""
controller.led_renderer
-----------------------

RingState から LED レベル配列を構築し monome Arc へ描画を行うレンダラ。
"""

import logging
from typing import Optional

import monome
from controller.led_styles import LED_STYLE_MAP, BaseLedStyle, get_led_instance
from model.model import RingState
from util.hardware_spec import ARC_SPEC, ArcSpec

LOGGER = logging.getLogger(__name__)


class LedRenderer:
    """
    RingState を LED へ描画する責務を持つクラス。

    Args:
        max_brightness (int): LED の最大輝度 (0‒15)。
        spec (ArcSpec | None): ハードウェア仕様 (リング数や LED 数など)。デフォルトは
            `ARC_SPEC`。
    """

    def __init__(self, max_brightness: int, spec: ArcSpec = ARC_SPEC):
        """依存オブジェクトを受け取り、LED レンダラの内部状態を初期化する。

        Args:
            max_brightness (int): LED の最大輝度 (0‒15)。
            spec (ArcSpec | None): ハードウェア仕様。デフォルトは `ARC_SPEC`。
        """
        self.max_brightness = max_brightness
        self.spec = spec
        self.arc: Optional[monome.Arc] = None
        self.buffer: Optional[monome.ArcBuffer] = None
        self._styles: dict[int, BaseLedStyle] = {}  # 各リングごとの LED スタイルを保持するキャッシュ
        self._last_levels: dict[int, list[int]] = {}  # 各リングごとの LED レベルを保持するキャッシュ

    def set_arc(self, arc: monome.Arc) -> None:
        """Arc インスタンスと描画バッファを設定する。

        Args:
            arc (monome.Arc): 接続済みの monome.Arc インスタンス。
        """
        self.arc = arc
        self.buffer = monome.ArcBuffer(rings=self.spec.rings_per_device)
        LOGGER.info("set monome.Arc and monome.ArcBuffer")

    def all_off(self) -> None:
        """全ての LED を消灯"""
        for n in range(self.spec.rings_per_device):
            self.arc.ring_all(n, 0)

    def render(self, ring_idx: int, ring_state: RingState) -> None:
        """RingState の値を LED へ描画する。

        Args:
            ring_idx (int): 描画対象リングのインデックス (0‒3)。
            ring_state (RingState): 現在値・スタイルなどを保持するデータクラス。

        Raises:
            RuntimeError: `set_arc()` を呼び出す前に実行された場合。
        """
        if self.arc is None or self.buffer is None:
            raise RuntimeError("call set_arc() before render()")

        levels = self._build_levels(ring_idx, ring_state)

        # 前フレームとの差分チェック ― 同一ならスキップ
        prev = self._last_levels.get(ring_idx)
        if prev is not None and prev == levels:
            # LOGGER.debug(f"levels unchanged, skip ring {ring_idx}")
            return

        # 変更があったので描画してキャッシュを更新
        self.buffer.ring_map(ring_idx, levels)
        self.buffer.render(self.arc)
        # list オブジェクトをそのまま保持すると次フレームで同じ参照が再利用され
        # 差分検出が効かないため copy() してスナップショット保存
        self._last_levels[ring_idx] = levels.copy()

    def _build_levels(self, ring_idx: int, ring_state: RingState) -> list[int]:
        """RingState から LED 輝度リストを生成し、必要に応じてスタイルを再生成する内部ヘルパ。

        Args:
            ring_idx (int): リングインデックス。
            ring_state (RingState): 対象リングの状態。

        Returns:
            list[int]: LED 輝度レベルのリスト (長さ 64)。
        """
        led_style = self._styles.get(ring_idx)
        # スタイルが変わった場合は新規インスタンス化
        if led_style is None or led_style.__class__ is not LED_STYLE_MAP.get(ring_state.led_style):
            before_style = None if led_style is None else led_style.style_enum
            LOGGER.info(f"LED style changed, re-instantiating. before={before_style}, after={ring_state.led_style}")
            led_style = get_led_instance(ring_state.led_style, self.max_brightness)
            self._styles[ring_idx] = led_style
        # レベルリストを生成
        return led_style.build_levels(ring_state.current_value, ring_state.value_style)
