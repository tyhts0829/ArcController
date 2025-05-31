"""
LED レンダラーのテスト

最小限のメンテナンスコストで最大の効果を得るため、
以下の重要な機能に焦点を当てたテストを実装します：
1. 基本的な初期化と設定
2. キャッシング機構（パフォーマンスに重要）
3. レンダリングブロック機能
4. エラーハンドリング
"""

import pytest
from unittest.mock import Mock, patch
from arc.services.renderers.led_renderer import LedRenderer
from arc.models.model import RingState, LayerState
from arc.enums.enums import LedStyle, ValueStyle
from arc.utils.hardware_spec import ARC_SPEC


class TestLedRenderer:
    """LedRenderer の基本機能テスト"""

    def test_init(self):
        """初期化時の状態を確認"""
        renderer = LedRenderer(max_brightness=10)
        assert renderer.max_brightness == 10
        assert renderer.spec == ARC_SPEC
        assert renderer.arc is None
        assert renderer.buffer is None
        assert renderer._styles == {}
        assert renderer._last_levels == {}
        assert renderer._render_blocked is False

    def test_set_arc(self):
        """Arc インスタンスの設定"""
        renderer = LedRenderer(max_brightness=10)
        mock_arc = Mock()
        
        renderer.set_arc(mock_arc)
        
        assert renderer.arc == mock_arc
        assert renderer.buffer is not None

    def test_require_arc_set_decorator(self):
        """Arc未設定時のエラーハンドリング"""
        renderer = LedRenderer(max_brightness=10)
        
        with pytest.raises(RuntimeError, match="call set_arc"):
            renderer.all_off()

    def test_all_off(self):
        """全LED消灯機能"""
        renderer = LedRenderer(max_brightness=10)
        mock_arc = Mock()
        renderer.set_arc(mock_arc)
        
        renderer.all_off()
        
        # 4つのリングすべてが消灯されることを確認
        assert mock_arc.ring_all.call_count == 4
        for i in range(4):
            mock_arc.ring_all.assert_any_call(i, 0)

    def test_highlight(self):
        """特定リングのハイライト機能"""
        renderer = LedRenderer(max_brightness=10)
        mock_arc = Mock()
        renderer.set_arc(mock_arc)
        
        renderer.highlight(ring_idx=2, level=5)
        
        # まず全消灯してから指定リングを点灯
        assert mock_arc.ring_all.call_count == 5  # 4 (all_off) + 1 (highlight)
        mock_arc.ring_all.assert_called_with(2, 5)

    def test_render_block(self):
        """レンダリングブロック機能"""
        renderer = LedRenderer(max_brightness=10)
        
        # ブロック設定
        renderer.set_render_block(blocked=True)
        assert renderer._render_blocked is True
        
        # ブロック解除
        renderer.set_render_block(blocked=False)
        assert renderer._render_blocked is False
        
        # 同じ状態を再設定しても変化なし
        renderer.set_render_block(blocked=False)
        assert renderer._render_blocked is False

    def test_render_value_with_cache(self):
        """キャッシュ機構を含むレンダリングテスト"""
        renderer = LedRenderer(max_brightness=10)
        mock_arc = Mock()
        mock_buffer = Mock()
        renderer.set_arc(mock_arc)
        renderer.buffer = mock_buffer
        
        ring_state = RingState(
            value=0.5,
            led_style=LedStyle.POTENTIOMETER,
            value_style=ValueStyle.LINEAR
        )
        
        # 初回レンダリング
        renderer.render_value(0, ring_state)
        assert mock_buffer.ring_map.call_count == 1
        assert mock_buffer.render.call_count == 1
        
        # 同じ状態で再レンダリング（キャッシュヒット）
        renderer.render_value(0, ring_state)
        assert mock_buffer.ring_map.call_count == 1  # 変化なし
        assert mock_buffer.render.call_count == 1    # 変化なし
        
        # 値を変更して再レンダリング
        ring_state.value = 0.7
        renderer.render_value(0, ring_state)
        assert mock_buffer.ring_map.call_count == 2
        assert mock_buffer.render.call_count == 2

    def test_render_value_ignore_cache(self):
        """ignore_cache パラメータのテスト"""
        renderer = LedRenderer(max_brightness=10)
        mock_arc = Mock()
        mock_buffer = Mock()
        renderer.set_arc(mock_arc)
        renderer.buffer = mock_buffer
        
        ring_state = RingState(
            value=0.5,
            led_style=LedStyle.DOT,
            value_style=ValueStyle.LINEAR
        )
        
        # 初回レンダリング
        renderer.render_value(0, ring_state)
        
        # ignore_cache=True で強制レンダリング
        renderer.render_value(0, ring_state, ignore_cache=True)
        assert mock_buffer.render.call_count == 2

    def test_render_blocked(self):
        """レンダリングブロック時の動作"""
        renderer = LedRenderer(max_brightness=10)
        mock_arc = Mock()
        mock_buffer = Mock()
        renderer.set_arc(mock_arc)
        renderer.buffer = mock_buffer
        renderer.set_render_block(blocked=True)
        
        ring_state = RingState(value=0.5)
        
        # ブロック中はレンダリングされない
        renderer.render_value(0, ring_state)
        assert mock_buffer.render.call_count == 0

    def test_render_layer(self):
        """レイヤー全体のレンダリング"""
        renderer = LedRenderer(max_brightness=10)
        mock_arc = Mock()
        mock_buffer = Mock()
        renderer.set_arc(mock_arc)
        renderer.buffer = mock_buffer
        
        # 4つのリングを持つレイヤー
        layer = LayerState([
            RingState(value=0.25, led_style=LedStyle.POTENTIOMETER),
            RingState(value=0.50, led_style=LedStyle.DOT),
            RingState(value=0.75, led_style=LedStyle.BIPOLAR),
            RingState(value=1.00, led_style=LedStyle.PERLIN),
        ])
        
        renderer.render_layer(layer)
        
        # 4つのリングがマップされ、1回だけレンダリング
        assert mock_buffer.ring_map.call_count == 4
        assert mock_buffer.render.call_count == 1

    def test_render_layer_partial_update(self):
        """レイヤーの部分更新（キャッシュ効果）"""
        renderer = LedRenderer(max_brightness=10)
        mock_arc = Mock()
        mock_buffer = Mock()
        renderer.set_arc(mock_arc)
        renderer.buffer = mock_buffer
        
        layer = LayerState([
            RingState(value=0.25),
            RingState(value=0.50),
            RingState(value=0.75),
            RingState(value=1.00),
        ])
        
        # 初回レンダリング
        renderer.render_layer(layer)
        mock_buffer.reset_mock()
        
        # 1つのリングだけ変更
        layer[1].value = 0.6
        renderer.render_layer(layer)
        
        # 変更されたリングだけマップされる
        assert mock_buffer.ring_map.call_count == 1
        assert mock_buffer.render.call_count == 1

    def test_style_change_detection(self):
        """LEDスタイル変更の検出と再インスタンス化"""
        renderer = LedRenderer(max_brightness=10)
        mock_arc = Mock()
        renderer.set_arc(mock_arc)
        renderer.buffer = Mock()
        
        ring_state = RingState(
            value=0.5,
            led_style=LedStyle.POTENTIOMETER,
            value_style=ValueStyle.LINEAR
        )
        
        # 初回レンダリング
        renderer.render_value(0, ring_state)
        initial_style = renderer._styles[0]
        
        # スタイルを変更
        ring_state.led_style = LedStyle.DOT
        renderer.render_value(0, ring_state)
        
        # 新しいスタイルインスタンスが作成される
        assert renderer._styles[0] != initial_style
        assert renderer._styles[0].__class__.__name__ == 'DotStyle'

    def test_build_levels_output(self):
        """_build_levels が正しい長さのリストを返すことを確認"""
        renderer = LedRenderer(max_brightness=10)
        ring_state = RingState(
            value=0.5,
            led_style=LedStyle.POTENTIOMETER,
            value_style=ValueStyle.LINEAR
        )
        
        levels = renderer._build_levels(0, ring_state)
        
        # Arc の LED は 64 個
        assert len(levels) == 64
        assert all(isinstance(level, int) for level in levels)
        assert all(0 <= level <= 15 for level in levels)

    @patch('arc.services.renderers.led_renderer.get_led_instance')
    def test_led_style_fallback(self, mock_get_led_instance):
        """未知のLEDスタイルに対するフォールバック"""
        renderer = LedRenderer(max_brightness=10)
        mock_style = Mock()
        mock_style.build_levels.return_value = [0] * 64
        mock_get_led_instance.return_value = mock_style
        
        ring_state = RingState(
            value=0.5,
            led_style=LedStyle.DOT,  # 任意のスタイル
            value_style=ValueStyle.LINEAR
        )
        
        levels = renderer._build_levels(0, ring_state)
        
        assert len(levels) == 64
        mock_get_led_instance.assert_called_once_with(LedStyle.DOT, 10)