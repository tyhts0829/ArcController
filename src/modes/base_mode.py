from abc import ABC, abstractmethod

import monome


class BaseMode(ABC):
    @abstractmethod
    def on_arc_ready(self, arc: monome.Arc) -> None: ...

    @abstractmethod
    def on_arc_disconnect(self) -> None: ...

    @abstractmethod
    def on_arc_delta(self, ring_idx: int, delta: int) -> None: ...

    @abstractmethod
    def on_arc_key(self, x: int, pressed: bool) -> None: ...
