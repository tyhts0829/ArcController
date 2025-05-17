"""LedRenderer の主要挙動を検証するテスト群。"""

import sys
import types
from types import SimpleNamespace

import pytest

# ---- 依存モジュールのスタブ作成 -------------------------------------------------


class DummyArc:
    """monome.Arc のテスト用スタブ。"""

    def __init__(self):
        self.calls = []

    def ring_all(self, ring_idx: int, level: int) -> None:
        """ring_all の呼び出しを記録のみ行う。"""
        self.calls.append(("ring_all", ring_idx, level))


class DummyArcBuffer:
    """monome.ArcBuffer のテスト用スタブ。"""

    def __init__(self, rings: int):
        self.rings = rings
        self.ring_calls: list[tuple[int, list[int]]] = []
        self.render_calls = 0

    # pylint: disable=unused-argument
    def ring_map(self, ring_idx: int, levels: list[int]) -> None:
        """ring_map の呼び出しを記録のみ行う。"""
        self.ring_calls.append((ring_idx, levels))

    def render(self, arc) -> None:  # noqa: D401  pylint: disable=unused-argument
        """呼び出し回数をカウントするだけ。"""
        self.render_calls += 1


class DummyLedStyle:
    """BaseLedStyle のテスト用スタブ。"""

    def __init__(self, style_enum, max_brightness):
        self.style_enum = style_enum
        self.max_brightness = max_brightness

    # pylint: disable=unused-argument
    def build_levels(self, current_value, value_style):
        """current_value を 64 要素に複製した配列を返す。"""
        return [current_value] * 64


# renderer.led_styles スタブ
led_styles_stub = types.ModuleType("renderer.led_styles")
led_styles_stub.LED_STYLE_MAP = {}
led_styles_stub.BaseLedStyle = DummyLedStyle
led_styles_stub.get_led_instance = lambda style_enum, max_brightness: DummyLedStyle(style_enum, max_brightness)

# monome スタブ
monome_stub = types.ModuleType("monome")
monome_stub.Arc = DummyArc
monome_stub.ArcBuffer = DummyArcBuffer


# ArcSpec スタブ
class DummyArcSpec:  # pylint: disable=too-few-public-methods
    """ArcSpec の最小実装。"""

    def __init__(self, rings_per_device: int):
        self.rings_per_device = rings_per_device


hardware_spec_stub = types.ModuleType("src.utils.hardware_spec")
hardware_spec_stub.ArcSpec = DummyArcSpec
hardware_spec_stub.ARC_SPEC = DummyArcSpec(2)

# パッケージ階層にスタブを挿入
src_pkg = types.ModuleType("src")
src_pkg.__path__ = []
utils_pkg = types.ModuleType("src.utils")
utils_pkg.__path__ = []
model_pkg = types.ModuleType("src.model")
model_pkg.__path__ = []

sys.modules.update(
    {
        "monome": monome_stub,
        "renderer.led_styles": led_styles_stub,
        "src": src_pkg,
        "src.utils": utils_pkg,
        "src.utils.hardware_spec": hardware_spec_stub,
        "src.model": model_pkg,
        "src.model.model": types.ModuleType("src.model.model"),
    }
)

# LedRenderer の実モジュールをインポート ― 依存スタブを注入済み
from renderer.led_renderer import (  # noqa: E402  pylint: disable=wrong-import-position
    LedRenderer,
)

# -------------------------------------------------------------


@pytest.fixture()
def renderer():
    """依存を差し替えた LedRenderer インスタンスを返す。"""
    spec = DummyArcSpec(2)
    return LedRenderer(max_brightness=15, spec=spec)


def test_all_off_before_set_arc_raises(renderer):
    """set_arc() 未呼び出し時に all_off() が RuntimeError を送出することを確認。"""
    with pytest.raises(RuntimeError):
        renderer.all_off()


def test_set_arc_and_all_off(renderer):
    """set_arc() 後に all_off() が各リングへ消灯コマンドを送ることを確認。"""
    arc = DummyArc()
    renderer.set_arc(arc)
    renderer.all_off()
    assert arc.calls == [("ring_all", 0, 0), ("ring_all", 1, 0)]


def test_highlight_calls_ring_all_sequence(renderer):
    """highlight() が消灯後に指定リングを点灯するシーケンスを実行することを確認。"""
    arc = DummyArc()
    renderer.set_arc(arc)
    renderer.highlight(1, level=5)
    assert arc.calls == [
        ("ring_all", 0, 0),
        ("ring_all", 1, 0),
        ("ring_all", 1, 5),
    ]


def test_render_value_renders_and_skips_when_unchanged(renderer):
    """render_value() が前フレームと値が同じ場合に描画をスキップする挙動を確認。"""
    arc = DummyArc()
    renderer.set_arc(arc)
    buffer = renderer.buffer  # type: ignore[attr-defined]
    ring_state = SimpleNamespace(current_value=3, led_style="dummy", value_style=None)

    # 初回描画 ― 実行されるはず
    renderer.render_value(0, ring_state)
    assert buffer.render_calls == 1

    # 2 回目は値が不変なのでスキップ
    renderer.render_value(0, ring_state)
    assert buffer.render_calls == 1

    # force=True なら強制描画
    renderer.render_value(0, ring_state, force=True)
    assert buffer.render_calls == 2


def test_render_layer_renders_each_ring(renderer):
    """render_layer() が全リングを描画することを確認。"""
    arc = DummyArc()
    renderer.set_arc(arc)
    ring_state0 = SimpleNamespace(current_value=1, led_style="dummy", value_style=None)
    ring_state1 = SimpleNamespace(current_value=2, led_style="dummy", value_style=None)

    renderer.render_layer([ring_state0, ring_state1])

    buffer = renderer.buffer  # type: ignore[attr-defined]
    # 2 つのリングに対して ring_map が 1 回ずつ呼ばれる
    assert [(0, 64), (1, 64)] == [(idx, len(levels)) for idx, levels in buffer.ring_calls]
    assert buffer.render_calls == 2
