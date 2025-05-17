"""
controller.layer_manager
------------------------

レイヤー（Model インスタンス集合）を管理し、現在アクティブなレイヤーを
循環させるユーティリティクラス。
"""

from typing import List

from model.model import Model


class LayerManager:
    """
    Model インスタンスのリストを束ね、現在レイヤーを管理するクラス。

    Args:
        layers (List[Model]): 管理対象となる Model のリスト。
        start_idx (int, optional): 初期レイヤー番号。デフォルトは 0。
    """

    def __init__(self, layers: List[Model], start_idx: int = 0) -> None:
        if not layers:
            raise ValueError("LayerManager requires at least one Model.")
        self._layers = layers
        self._idx = start_idx % len(layers)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @property
    def current(self) -> Model:
        """現在アクティブな Model を返す。"""
        return self._layers[self._idx]

    @property
    def index(self) -> int:
        """現在のレイヤー番号 (0‑based)。"""
        return self._idx

    def next(self) -> None:
        """レイヤーを 1 つ進め、循環させる。"""
        self._idx = (self._idx + 1) % len(self._layers)
