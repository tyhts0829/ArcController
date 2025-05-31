"""
Controllerクラスのテスト

最小限のメンテナンスコストで最大の効果を得るため、
以下の重要な機能に焦点を当てたテストを実装：
1. 初期化とステートマシンの設定
2. キーイベント処理（押下/離上）
3. 長押し検出機能
4. ダイヤルイベントの委譲
5. デバイス接続/切断処理
6. 状態遷移の正確性
"""

from unittest.mock import Mock, patch
import pytest
import transitions
from arc.controller.controller import Controller, STATES
from arc.models.model import Model
from arc.enums.enums import Mode
from arc.modes.ready_mode import ReadyMode
from arc.modes.value_send_mode import ValueSendMode
from arc.modes.layer_select_mode import LayerSelectMode
from arc.modes.preset_select_mode import PresetSelectMode
from arc.modes.disconnect_mode import DisconnectMode


class TestController:
    """Controllerの基本機能テスト"""

    @pytest.fixture
    def mock_modes(self):
        """モックモードのフィクスチャ"""
        # 型ヒント警告を回避するため、適切にspecを設定
        ready_mode = Mock(spec=ReadyMode)
        value_send_mode = Mock(spec=ValueSendMode)
        layer_select_mode = Mock(spec=LayerSelectMode)
        preset_select_mode = Mock(spec=PresetSelectMode)
        disconnect_mode = Mock(spec=DisconnectMode)
        
        # 型ヒント問題を回避するためのマッピング
        return {
            Mode.READY_MODE: ready_mode,
            Mode.VALUE_SEND_MODE: value_send_mode,
            Mode.LAYER_SELECT_MODE: layer_select_mode,
            Mode.PRESET_SELECT_MODE: preset_select_mode,
            Mode.DISCONNECT_MODE: disconnect_mode,
        }

    @pytest.fixture
    def controller(self, mock_modes):
        """テスト用コントローラのフィクスチャ"""
        model = Mock(spec=Model)
        return Controller(model=model, mode_mapping=mock_modes, long_press_duration=0.2)

    def test_init(self, mock_modes):
        """初期化時の各プロパティが正しく設定されることを確認"""
        model = Mock(spec=Model)
        controller = Controller(model=model, mode_mapping=mock_modes, long_press_duration=0.3)
        
        assert controller.model == model
        assert controller._modes == mock_modes
        assert controller._long_press_duration == 0.3
        assert controller._is_pressed is False
        assert controller._long_press_timer is None
        assert controller.state == Mode.VALUE_SEND_MODE  # 初期状態

    def test_state_machine_setup(self, controller):
        """ステートマシンが正しく設定されることを確認"""
        assert controller.machine is not None
        assert len(controller.machine.states) == len(STATES)
        assert controller.state == Mode.VALUE_SEND_MODE

    def test_on_arc_key_pressed(self, controller):
        """キー押下イベントが正しく処理されることを確認"""
        with patch.object(controller, '_on_key_pressed') as mock_pressed:
            controller.on_arc_key(0, True)
            mock_pressed.assert_called_once()

    def test_on_arc_key_released(self, controller):
        """キー離上イベントが正しく処理されることを確認"""
        with patch.object(controller, '_on_key_released') as mock_released:
            controller.on_arc_key(0, False)
            mock_released.assert_called_once()

    def test_key_press_triggers_state_transition(self, controller):
        """キー押下でレイヤー選択モードに遷移することを確認"""
        with patch('asyncio.get_running_loop') as mock_loop:
            mock_loop.return_value.call_later = Mock()
            controller.on_arc_key(0, True)
            assert controller.state == Mode.LAYER_SELECT_MODE

    def test_key_release_returns_to_value_send(self, controller):
        """キー離上で値送信モードに戻ることを確認"""
        with patch('asyncio.get_running_loop') as mock_loop:
            mock_timer = Mock()
            mock_loop.return_value.call_later = Mock(return_value=mock_timer)
            controller.on_arc_key(0, True)  # まずレイヤー選択モードへ
            controller.on_arc_key(0, False)  # 離して値送信モードへ
            assert controller.state == Mode.VALUE_SEND_MODE

    @pytest.mark.asyncio
    async def test_long_press_detection(self, controller):
        """長押しが正しく検出されることを確認"""
        # イベントループのコンテキストで実行
        with patch('asyncio.get_running_loop') as mock_loop:
            mock_timer = Mock()
            mock_loop.return_value.call_later = Mock(return_value=mock_timer)
            
            # 押下してレイヤー選択モードへ
            controller.on_arc_key(0, True)
            assert controller.state == Mode.LAYER_SELECT_MODE
            
            # call_laterが呼ばれたことを確認
            mock_loop.return_value.call_later.assert_called_once_with(
                0.2, controller._on_long_press
            )
            
            # 長押しコールバックを手動で実行
            controller._on_long_press()
            assert controller.state == Mode.PRESET_SELECT_MODE

    def test_long_press_timer_cancelled_on_release(self, controller):
        """離上時に長押しタイマーがキャンセルされることを確認"""
        with patch('asyncio.get_running_loop') as mock_loop:
            mock_timer = Mock()
            mock_loop.return_value.call_later = Mock(return_value=mock_timer)
            
            # 押下
            controller.on_arc_key(0, True)
            assert controller._long_press_timer == mock_timer
            
            # 離上
            controller.on_arc_key(0, False)
            mock_timer.cancel.assert_called_once()
            assert controller._long_press_timer is None

    def test_on_arc_delta_delegates_to_current_mode(self, controller, mock_modes):
        """ダイヤルイベントが現在のモードに委譲されることを確認"""
        # 値送信モードでのダイヤル操作
        controller.on_arc_delta(1, 10)
        mock_modes[Mode.VALUE_SEND_MODE].on_arc_delta.assert_called_once_with(1, 10)
        
        # レイヤー選択モードに切り替えてダイヤル操作
        with patch('asyncio.get_running_loop') as mock_loop:
            mock_loop.return_value.call_later = Mock()
            controller.on_arc_key(0, True)
            controller.on_arc_delta(2, -5)
            mock_modes[Mode.LAYER_SELECT_MODE].on_arc_delta.assert_called_once_with(2, -5)

    def test_on_arc_delta_with_none_state(self, controller):
        """状態がNoneの場合のダイヤルイベント処理を確認"""
        controller.state = None
        with patch('arc.controller.controller.LOGGER') as mock_logger:
            controller.on_arc_delta(0, 10)
            mock_logger.error.assert_called_once()

    def test_on_arc_delta_with_unknown_state(self, controller):
        """未知の状態でのダイヤルイベント処理を確認"""
        controller.state = "UNKNOWN_STATE"
        with patch('arc.controller.controller.LOGGER') as mock_logger:
            controller.on_arc_delta(0, 10)
            mock_logger.error.assert_called_once()

    def test_on_arc_ready(self, controller, mock_modes):
        """デバイス接続時の処理を確認"""
        mock_arc = Mock()
        controller.arc = mock_arc
        
        controller.on_arc_ready()
        
        # 値送信モードに遷移
        assert controller.state == Mode.VALUE_SEND_MODE
        # ReadyModeのon_arc_readyが呼ばれる
        mock_modes[Mode.READY_MODE].on_arc_ready.assert_called_once_with(mock_arc)

    def test_on_arc_disconnect(self, controller, mock_modes):
        """デバイス切断時の処理を確認"""
        controller.on_arc_disconnect()
        
        # 切断モードに遷移
        assert controller.state == Mode.DISCONNECT_MODE
        # DisconnectModeのon_arc_disconnectが呼ばれる
        mock_modes[Mode.DISCONNECT_MODE].on_arc_disconnect.assert_called_once()

    def test_state_enter_exit_callbacks(self, controller, mock_modes):
        """状態遷移時のenter/exitコールバックが呼ばれることを確認"""
        with patch('asyncio.get_running_loop') as mock_loop:
            mock_timer = Mock()
            mock_loop.return_value.call_later = Mock(return_value=mock_timer)
            
            # レイヤー選択モードへの遷移
            controller.on_arc_key(0, True)
            mock_modes[Mode.LAYER_SELECT_MODE].on_enter.assert_called_once()
            
            # プリセット選択モードへの遷移（レイヤー選択モードから）
            controller._on_long_press()
            mock_modes[Mode.LAYER_SELECT_MODE].on_exit.assert_called_once()
            mock_modes[Mode.PRESET_SELECT_MODE].on_enter.assert_called_once()
            
            # 値送信モードへ戻る
            controller.on_arc_key(0, False)
            mock_modes[Mode.PRESET_SELECT_MODE].on_exit.assert_called_once()

    def test_multiple_key_presses(self, controller):
        """複数回のキー押下が正しく処理されることを確認"""
        with patch('asyncio.get_running_loop') as mock_loop:
            mock_timer = Mock()
            mock_loop.return_value.call_later = Mock(return_value=mock_timer)
            
            # 押下→離上を繰り返す
            for _ in range(3):
                controller.on_arc_key(0, True)
                assert controller.state == Mode.LAYER_SELECT_MODE
                controller.on_arc_key(0, False)
                assert controller.state == Mode.VALUE_SEND_MODE

    def test_custom_long_press_duration(self):
        """カスタム長押し時間が正しく使用されることを確認"""
        model = Mock(spec=Model)
        
        # 型ヒント警告を回避するため、適切にspecを設定
        ready_mode = Mock(spec=ReadyMode)
        value_send_mode = Mock(spec=ValueSendMode)
        layer_select_mode = Mock(spec=LayerSelectMode)
        preset_select_mode = Mock(spec=PresetSelectMode)
        disconnect_mode = Mock(spec=DisconnectMode)
        
        modes = {
            Mode.READY_MODE: ready_mode,
            Mode.VALUE_SEND_MODE: value_send_mode,
            Mode.LAYER_SELECT_MODE: layer_select_mode,
            Mode.PRESET_SELECT_MODE: preset_select_mode,
            Mode.DISCONNECT_MODE: disconnect_mode,
        }
        controller = Controller(model=model, mode_mapping=modes, long_press_duration=0.5)  # type: ignore[arg-type]
        
        with patch('asyncio.get_running_loop') as mock_loop:
            mock_loop.return_value.call_later = Mock()
            
            controller._start_long_press_timer()
            
            # 0.5秒でcall_laterが呼ばれることを確認
            mock_loop.return_value.call_later.assert_called_once_with(
                0.5, controller._on_long_press
            )


class TestControllerStateTransitions:
    """状態遷移の詳細なテスト"""

    @pytest.fixture
    def controller(self):
        """シンプルなコントローラのフィクスチャ"""
        model = Mock(spec=Model)
        
        # 型ヒント警告を回避するため、適切にspecを設定
        ready_mode = Mock(spec=ReadyMode)
        value_send_mode = Mock(spec=ValueSendMode)
        layer_select_mode = Mock(spec=LayerSelectMode)
        preset_select_mode = Mock(spec=PresetSelectMode)
        disconnect_mode = Mock(spec=DisconnectMode)
        
        modes = {
            Mode.READY_MODE: ready_mode,
            Mode.VALUE_SEND_MODE: value_send_mode,
            Mode.LAYER_SELECT_MODE: layer_select_mode,
            Mode.PRESET_SELECT_MODE: preset_select_mode,
            Mode.DISCONNECT_MODE: disconnect_mode,
        }
        return Controller(model=model, mode_mapping=modes)  # type: ignore[arg-type]

    def test_all_state_transitions(self, controller):
        """すべての状態遷移パスをテスト"""
        # 初期状態
        assert controller.state == Mode.VALUE_SEND_MODE
        
        # VALUE_SEND → LAYER_SELECT
        controller.trigger("press")
        assert controller.state == Mode.LAYER_SELECT_MODE
        
        # LAYER_SELECT → PRESET_SELECT
        controller.trigger("long_press")
        assert controller.state == Mode.PRESET_SELECT_MODE
        
        # PRESET_SELECT → VALUE_SEND
        controller.trigger("release")
        assert controller.state == Mode.VALUE_SEND_MODE
        
        # Any → DISCONNECT
        controller.trigger("_on_arc_disconnect")
        assert controller.state == Mode.DISCONNECT_MODE
        
        # DISCONNECT → VALUE_SEND (on ready)
        controller.trigger("_on_arc_ready")
        assert controller.state == Mode.VALUE_SEND_MODE

    def test_state_persistence_during_invalid_triggers(self, controller):
        """無効なトリガーでは状態が変化しないことを確認"""
        # VALUE_SENDモードで長押し（無効なトリガー）
        controller.state = Mode.VALUE_SEND_MODE
        with pytest.raises(transitions.core.MachineError):
            controller.trigger("long_press")
        # 状態は変わらない
        assert controller.state == Mode.VALUE_SEND_MODE