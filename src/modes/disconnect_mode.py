from __future__ import annotations

import monome

from lfo.lfo_engine import LfoEngine
from src.modes.base_mode import BaseMode


class DisconnectMode(BaseMode):
    """Arc デバイスが切断されたときに呼ばれるモード。"""

    def __init__(self, lfo_engine: LfoEngine) -> None:
        self._lfo_engine = lfo_engine

    def on_arc_ready(self, arc: monome.Arc) -> None:
        pass

    def on_arc_disconnect(self) -> None:
        self._lfo_engine.stop()

    def on_arc_delta(self, ring_idx: int, delta: int) -> None:
        pass

    def on_arc_key(self, x: int, pressed: bool) -> None:
        pass
