import pytest

from controller.preset_manager import PresetManager
from model.model import RingState


@pytest.fixture
def sample_presets():
    """テスト用のダミープリセットを返す。"""
    return [
        {
            "name": "PresetA",
            "value_style": "linear",
            "led_style": "perlin",
            "lfo_style": "perlin",
        },
        {
            "name": "PresetB",
            "value_style": "bipolar",
            "led_style": "dot",
            "lfo_style": "static",
        },
        {
            "name": "PresetC",
            "value_style": "infinite",
            "led_style": "potentiometer",
            "lfo_style": "random",
        },
    ]


@pytest.fixture
def ring_state():
    """プリセットインデックスを持つダミーRingStateを返す。"""
    # 本来の Model / RingState から生成でも良いが、ここでは簡易化
    return RingState(preset_index=0, current_value=0.0)  # 最初は PresetA (インデックス0)


@pytest.fixture
def manager(sample_presets):
    """threshold=10, num_rings=1 で PresetManager を初期化して返す。"""
    # リング1本だけ管理すると仮定
    return PresetManager(presets=sample_presets, threshold=10, num_rings=1)


def test_no_change_under_threshold(manager, ring_state):
    """
    Δ が threshold 未満のままではプリセットが切り替わらず、
    戻り値がFalseになることを確認。
    """
    # ring_idx=0、delta=9なら threshold=10 に満たないので切り替わらない
    changed = manager.process_delta(0, 9, ring_state)
    assert changed is False
    # インデックス変化なし
    assert ring_state.preset_index == 0


def test_change_when_threshold_exceeded(manager, ring_state):
    """
    Δ が累積で threshold を超えたときにプリセットが切り替わり、
    戻り値がTrueになることを確認。
    """
    # まず9だけでは変化しない
    manager.process_delta(0, 9, ring_state)
    assert ring_state.preset_index == 0

    # さらに +2 (合計11) => threshold=10 を超える => 1ステップ進む
    changed = manager.process_delta(0, 2, ring_state)
    assert changed is True
    # プリセットインデックスが1つ進む: 0 -> 1
    assert ring_state.preset_index == 1


def test_preset_cycling_forward(manager, ring_state):
    """
    正方向(正のΔ)に大きく動かしてプリセットインデックスを複数回循環させる。
    """
    # プリセット数は3つ: 0, 1, 2
    # threshold=10 のとき、1周するには30以上必要(3ステップ進む)

    # delta=35 -> steps=3 (35//10=3)
    #   新インデックス = (0 + 3) % 3 = 0 (ちょうど一周＋さらに少し)
    changed = manager.process_delta(0, 35, ring_state)
    assert changed is True
    # 0 -> 0 に戻る
    assert ring_state.preset_index == 0

    # 追加で +10 = 1ステップぶん
    manager.process_delta(0, 10, ring_state)
    assert ring_state.preset_index == 1


def test_preset_cycling_backward(manager, ring_state):
    """
    負のΔでプリセットインデックスを逆方向に循環させる。
    """
    # ring_state初期インデックス=0
    # delta=-10 => steps=-1 => (0 + -1) % 3 = 2
    changed = manager.process_delta(0, -10, ring_state)
    assert changed is True
    assert ring_state.preset_index == 2  # 後ろ方向に1つ

    # さらに -10 => steps=-1 => 2 -> 1
    manager.process_delta(0, -10, ring_state)
    assert ring_state.preset_index == 1


def test_multiple_steps_in_one_delta(manager, ring_state):
    """
    1回の delta で複数ステップ進む場合の挙動を確認。
    """
    # delta=25 => steps=2 (25//10=2)
    # 新インデックス = (0 + 2) % 3 = 2
    changed = manager.process_delta(0, 25, ring_state)
    assert changed is True
    assert ring_state.preset_index == 2


def test_reset_accumulated_delta(manager, ring_state):
    """
    reset() を呼ぶと累積 Δ がクリアされることを確認。
    """
    # まず threshold未満(9)を加算
    manager.process_delta(0, 9, ring_state)
    # まだプリセット切り替えは起きない
    assert ring_state.preset_index == 0

    # resetで累積された 9 をクリア
    manager.reset()

    # 再度1だけ足しても、threshold=10 に遠い → 切り替わらず
    changed = manager.process_delta(0, 1, ring_state)
    assert changed is False
    assert ring_state.preset_index == 0


@pytest.fixture
def multi_ring_manager(sample_presets):
    """
    複数リング(num_rings=4)を想定したPresetManagerを返すfixture。
    threshold=10は変えずに、リングごとのテストを行う。
    """
    return PresetManager(presets=sample_presets, threshold=10, num_rings=4)


def test_multiple_rings_mixed_deltas(multi_ring_manager, sample_presets):
    """
    異なるリングに対して混在したΔを操作した場合のプリセット切り替え動作を検証する。
    リング0,1,2,3がそれぞれ独立に累積Δを持つことを確認。
    """
    # 4つのリング状態を用意 (最初は全てpreset_index=0)
    ring_states = [RingState(preset_index=0) for _ in range(4)]

    # Ring 0: +12 => threshold=10 を超える => 1ステップ進む -> preset_index=1 へ
    changed0 = multi_ring_manager.process_delta(0, 12, ring_states[0])
    assert changed0 is True
    assert ring_states[0].preset_index == 1
    assert ring_states[0].lfo_style.value == sample_presets[1]["lfo_style"]  # 'static'のはず

    # Ring 1: +5 => threshold未満 => preset_indexは変化なし (0のまま)
    changed1 = multi_ring_manager.process_delta(1, 5, ring_states[1])
    assert changed1 is False
    assert ring_states[1].preset_index == 0

    # Ring 2: -20 => steps=-2 => (0 + -2) % 3 = 1 -> preset_index=1
    changed2 = multi_ring_manager.process_delta(2, -20, ring_states[2])
    assert changed2 is True
    assert ring_states[2].preset_index == 1
    assert ring_states[2].value_style.value == sample_presets[1]["value_style"]  # 'bipolar'

    # Ring 3: 2回に分けて累積する
    #   1回目: +9 => threshold未満 => 変化なし
    changed3_part1 = multi_ring_manager.process_delta(3, 9, ring_states[3])
    assert changed3_part1 is False
    assert ring_states[3].preset_index == 0

    #   2回目: +2 => 合計+11 => threshold=10 を超える => 1ステップ進む -> preset_index=1
    changed3_part2 = multi_ring_manager.process_delta(3, 2, ring_states[3])
    assert changed3_part2 is True
    assert ring_states[3].preset_index == 1
    assert ring_states[3].led_style.value == sample_presets[1]["led_style"]  # 'dot'

    # 最終的に、ring0,2,3はpreset_index=1, ring1は0のままである
    assert [r.preset_index for r in ring_states] == [1, 0, 1, 1]
