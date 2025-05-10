import logging
from typing import Optional

import monome
from controller.led_styles import LED_STYLE_MAP, BaseLedStyle, get_led_instance
from model.model import RingState
from util.hardware_spec import ARC_SPEC, ArcSpec

LOGGER = logging.getLogger(__name__)


class LedRenderer:
    def __init__(self, max_brightness: int, spec: ArcSpec = ARC_SPEC):
        self.max_brightness = max_brightness
        self.spec = spec
        self.arc: Optional[monome.Arc] = None
        self.buffer: Optional[monome.ArcBuffer] = None
        # 各リングごとに保持するスタイルレンダラー
        self._style_renderers: dict[int, BaseLedStyle] = {}
        # 前回描画した LED レベルをリング毎にキャッシュ
        self._last_levels: dict[int, list[int]] = {}

    def set_arc(self, arc: monome.Arc) -> None:
        self.arc = arc
        self.buffer = monome.ArcBuffer(rings=self.spec.rings_per_device)
        LOGGER.info("set monome.Arc and monome.ArcBuffer")

    def all_off(self) -> None:
        """全ての LED を消灯"""
        for n in range(self.spec.rings_per_device):
            self.arc.ring_all(n, 0)

    def render(self, ring_idx: int, ring_state: RingState) -> None:
        """RingState の値を LED へ描画。Arc がまだ無い場合は無視。"""
        if self.arc is None or self.buffer is None:
            raise RuntimeError("call set_arc() before render()")

        levels = self._build_levels(ring_idx, ring_state)

        # 前フレームとの差分チェック ― 同一ならスキップ
        prev = self._last_levels.get(ring_idx)
        if prev is not None and prev == levels:
            LOGGER.debug(f"levels unchanged, skip ring {ring_idx}")
            return

        # 変更があったので描画してキャッシュを更新
        self.buffer.ring_map(ring_idx, levels)
        self.buffer.render(self.arc)
        # list オブジェクトをそのまま保持すると次フレームで同じ参照が再利用され
        # 差分検出が効かないため copy() してスナップショット保存
        self._last_levels[ring_idx] = levels.copy()

    def _build_levels(self, ring_idx: int, ring_state: RingState) -> list[int]:
        # リングごとのレンダラーを取得または生成
        renderer = self._style_renderers.get(ring_idx)
        # スタイルが変わった場合は新規インスタンス化
        if renderer is None or renderer.__class__ is not LED_STYLE_MAP.get(ring_state.led_style):
            LOGGER.info(f"LED style changed, re-instantiating. before={renderer}, after={ring_state.led_style}")
            renderer = get_led_instance(ring_state.led_style, self.max_brightness)
            self._style_renderers[ring_idx] = renderer
        # レベルリストを生成
        return renderer.build_levels(ring_state.current_value, ring_state.value_style)
