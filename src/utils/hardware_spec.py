from dataclasses import dataclass


@dataclass(frozen=True)
class ArcSpec:
    """Arc 本体の不変なハードウェア仕様"""

    rings_per_device: int = 4
    leds_per_ring: int = 64


ARC_SPEC = ArcSpec()
