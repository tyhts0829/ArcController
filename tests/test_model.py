"""
Modelクラスのテスト

最小限のメンテナンスコストで最大の効果を得るため、
以下の重要な機能に焦点を当てたテストを実装します：
1. Model/LayerState/RingStateの基本的な初期化と構造
2. 値の更新とクランプ処理（境界値テスト）
3. プリセットシステム
4. レイヤー切り替え機能
5. 設定からの初期化
"""

import pytest
from unittest.mock import Mock
from arc.models.model import Model, LayerState, RingState
from arc.enums.enums import ValueStyle, LedStyle, LfoStyle
from arc.utils.hardware_spec import ARC_SPEC


class TestRingState:
    """RingState の基本機能テスト"""

    def test_init_defaults(self):
        """デフォルト値での初期化"""
        ring = RingState()
        assert ring.value == 0.0
        assert ring.cc_number == 0
        assert ring.value_style == ValueStyle.LINEAR
        assert ring.led_style == LedStyle.PERLIN
        assert ring.lfo_style == LfoStyle.PERLIN
        assert ring.lfo_frequency == 0.5
        assert ring.lfo_amplitude == 0.5
        assert ring.lfo_phase == 0.0
        assert ring.preset_index == 0
        assert ring.value_gain == 0.001
        assert ring.lfo_freq_gain == 0.0005

    def test_apply_delta_linear(self):
        """LINEAR スタイルでの値更新とクランプ"""
        ring = RingState(value=0.5, value_style=ValueStyle.LINEAR)
        
        # 通常の更新
        ring.apply_delta(100)
        assert ring.value == 0.6  # 0.5 + 100 * 0.001
        
        # 上限クランプ
        ring.value = 0.95
        ring.apply_delta(100)
        assert ring.value == 1.0
        
        # 下限クランプ
        ring.value = 0.05
        ring.apply_delta(-100)
        assert ring.value == 0.0

    def test_apply_delta_infinite(self):
        """INFINITE スタイルでの値更新（クランプなし）"""
        ring = RingState(value=0.5, value_style=ValueStyle.INFINITE)
        
        # 上限を超える
        ring.apply_delta(1000)
        assert ring.value == 1.5  # クランプされない
        
        # 下限を超える
        ring.value = 0.5
        ring.apply_delta(-1000)
        assert ring.value == -0.5  # クランプされない

    def test_apply_lfo_delta(self):
        """LFO周波数の更新とクランプ"""
        ring = RingState(lfo_frequency=0.5)
        
        # 通常の更新
        ring.apply_lfo_delta(100)
        assert ring.lfo_frequency == 0.55  # 0.5 + 100 * 0.0005
        
        # 上限クランプ
        ring.lfo_frequency = 0.95
        ring.apply_lfo_delta(200)
        assert ring.lfo_frequency == 1.0
        
        # 下限クランプ
        ring.lfo_frequency = 0.05
        ring.apply_lfo_delta(-200)
        assert ring.lfo_frequency == 0.0

    def test_apply_preset(self):
        """プリセット適用"""
        ring = RingState()
        preset = {
            "value_style": "bipolar",
            "led_style": "dot",
            "lfo_style": "static"
        }
        
        ring.apply_preset(preset)
        
        assert ring.value_style == ValueStyle.BIPOLAR
        assert ring.led_style == LedStyle.DOT
        assert ring.lfo_style == LfoStyle.STATIC
        assert ring.value == 0.5  # BIPOLARの場合は0.5にリセット

    def test_apply_preset_bipolar_value_reset(self):
        """BIPOLARプリセット適用時の値リセット"""
        ring = RingState(value=0.2)
        
        # LED_STYLEがBIPOLARの場合
        preset = {
            "value_style": "linear",
            "led_style": "bipolar",
            "lfo_style": "static"
        }
        ring.apply_preset(preset)
        assert ring.value == 0.5
        
        # VALUE_STYLEがBIPOLARの場合
        ring.value = 0.2
        preset = {
            "value_style": "bipolar",
            "led_style": "dot",
            "lfo_style": "static"
        }
        ring.apply_preset(preset)
        assert ring.value == 0.5

    def test_cycle_preset(self):
        """プリセットサイクル"""
        ring = RingState()
        presets = [
            {"value_style": "linear", "led_style": "potentiometer", "lfo_style": "static"},
            {"value_style": "bipolar", "led_style": "bipolar", "lfo_style": "perlin"},
            {"value_style": "infinite", "led_style": "dot", "lfo_style": "random_ease"},
        ]
        ring.set_presets(presets)
        
        # 順方向サイクル
        assert ring.preset_index == 0
        ring.cycle_preset(1)
        assert ring.preset_index == 1
        assert ring.value_style == ValueStyle.BIPOLAR
        
        ring.cycle_preset(1)
        assert ring.preset_index == 2
        assert ring.value_style == ValueStyle.INFINITE
        
        # ラップアラウンド
        ring.cycle_preset(1)
        assert ring.preset_index == 0
        assert ring.value_style == ValueStyle.LINEAR
        
        # 逆方向サイクル
        ring.cycle_preset(-1)
        assert ring.preset_index == 2

    def test_cycle_preset_empty_list(self):
        """空のプリセットリストでのサイクル（エラーハンドリング）"""
        ring = RingState()
        ring.set_presets([])
        
        # エラーは発生しない
        ring.cycle_preset(1)
        assert ring.preset_index == 0


class TestLayerState:
    """LayerState の基本機能テスト"""

    def test_init_defaults(self):
        """デフォルトでの初期化"""
        layer = LayerState()
        assert len(layer.rings) == ARC_SPEC.rings_per_device
        assert layer.name == "Layer"
        assert all(isinstance(ring, RingState) for ring in layer.rings)

    def test_getitem(self):
        """インデックスアクセス"""
        layer = LayerState()
        ring = layer[0]
        assert isinstance(ring, RingState)
        assert ring is layer.rings[0]

    def test_iteration(self):
        """イテレーション"""
        layer = LayerState()
        rings = list(layer)
        assert len(rings) == ARC_SPEC.rings_per_device
        assert all(isinstance(ring, RingState) for ring in rings)


class TestModel:
    """Model の基本機能テスト"""

    def test_init_defaults(self):
        """デフォルトでの初期化"""
        model = Model()
        assert model.num_layers == 4
        assert len(model.layers) == 4
        assert model.active_layer_idx == 0
        assert all(isinstance(layer, LayerState) for layer in model.layers)

    def test_init_custom_layers(self):
        """カスタムレイヤー数での初期化"""
        model = Model(num_layers=8)
        assert model.num_layers == 8
        assert len(model.layers) == 8

    def test_active_layer_property(self):
        """アクティブレイヤーのプロパティ"""
        model = Model()
        assert model.active_layer is model.layers[0]
        
        model.active_layer_idx = 2
        assert model.active_layer is model.layers[2]

    def test_cycle_layer(self):
        """レイヤーサイクル"""
        model = Model(num_layers=4)
        
        # 順方向
        assert model.active_layer_idx == 0
        model.cycle_layer(1)
        assert model.active_layer_idx == 1
        
        # 複数ステップ
        model.cycle_layer(2)
        assert model.active_layer_idx == 3
        
        # ラップアラウンド
        model.cycle_layer(1)
        assert model.active_layer_idx == 0
        
        # 逆方向
        model.cycle_layer(-1)
        assert model.active_layer_idx == 3

    def test_getitem(self):
        """リングへの直接アクセス"""
        model = Model()
        ring = model[0]
        assert isinstance(ring, RingState)
        assert ring is model.active_layer[0]

    def test_iteration(self):
        """レイヤーのイテレーション"""
        model = Model(num_layers=3)
        layers = list(model)
        assert len(layers) == 3
        assert all(isinstance(layer, LayerState) for layer in layers)

    def test_from_config(self):
        """設定からの初期化"""
        # モックの設定オブジェクト
        cfg = Mock()
        cfg.model.num_layers = 2
        cfg.presets = [
            {"value_style": "linear", "led_style": "potentiometer", "lfo_style": "static"},
            {"value_style": "bipolar", "led_style": "bipolar", "lfo_style": "perlin"},
        ]
        
        model = Model.from_config(cfg, cc_base=1)
        
        # レイヤー数
        assert model.num_layers == 2
        assert len(model.layers) == 2
        
        # CC番号の割り当て（1-8 for 2 layers × 4 rings）
        expected_cc = 1
        for layer in model.layers:
            for ring in layer:
                assert ring.cc_number == expected_cc
                expected_cc += 1
        
        # プリセットの適用
        for layer in model.layers:
            for ring in layer:
                assert ring.value_style == ValueStyle.LINEAR
                assert ring.led_style == LedStyle.POTENTIOMETER
                assert ring.lfo_style == LfoStyle.STATIC

    def test_from_config_missing_num_layers(self):
        """設定にnum_layersがない場合のフォールバック"""
        cfg = Mock()
        # AttributeErrorを発生させる
        cfg.model = Mock(spec=[])
        cfg.senders = Mock(spec=[])
        cfg.presets = [
            {"value_style": "linear", "led_style": "potentiometer", "lfo_style": "static"}
        ]
        
        model = Model.from_config(cfg)  # cc_baseはデフォルト値0を使用
        
        # デフォルトの4レイヤーにフォールバック
        assert model.num_layers == 4
        assert len(model.layers) == 4
        
        # CC番号もデフォルト値0から開始
        assert model.layers[0].rings[0].cc_number == 0

    def test_layer_names(self):
        """レイヤー名の自動生成"""
        model = Model(num_layers=3)
        assert model.layers[0].name == "L0"
        assert model.layers[1].name == "L1"
        assert model.layers[2].name == "L2"


class TestIntegration:
    """統合テスト：複数コンポーネントの連携"""

    def test_full_preset_cycle_workflow(self):
        """完全なプリセットサイクルワークフロー"""
        # 設定からモデルを作成
        cfg = Mock()
        cfg.model.num_layers = 1
        cfg.presets = [
            {"value_style": "linear", "led_style": "potentiometer", "lfo_style": "static"},
            {"value_style": "midi_7_bit", "led_style": "dot", "lfo_style": "perlin"},
        ]
        
        model = Model.from_config(cfg, cc_base=0)
        ring = model[0]
        
        # 初期状態
        assert ring.preset_index == 0
        assert ring.value_style == ValueStyle.LINEAR
        
        # プリセット切り替え
        ring.cycle_preset()
        assert ring.preset_index == 1
        assert ring.value_style == ValueStyle.MIDI_7BIT
        assert ring.led_style == LedStyle.DOT
        
        # 値の更新
        ring.apply_delta(500)
        assert 0 <= ring.value <= 1  # MIDI_7BITでもクランプされる

    def test_layer_switching_preserves_state(self):
        """レイヤー切り替え時の状態保持"""
        model = Model(num_layers=2)
        
        # レイヤー0のリング0を更新
        model.active_layer_idx = 0
        model[0].value = 0.7
        
        # レイヤー1に切り替えて更新
        model.cycle_layer()
        model[0].value = 0.3
        
        # レイヤー0に戻る
        model.cycle_layer()
        assert model[0].value == 0.7  # 値が保持されている
        
        # レイヤー1の値も保持されている
        model.cycle_layer()
        assert model[0].value == 0.3