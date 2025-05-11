import pytest

from util.util import clamp


@pytest.mark.parametrize(
    "x, lo, hi, expected",
    [
        (0.5, 0.0, 1.0, 0.5),  # 値が範囲内
        (-1, 0, 10, 0),  # 下限未満 → lo に丸め
        (15, 0, 10, 10),  # 上限超過 → hi に丸め
        (0, 0, 10, 0),  # 下限境界
        (10, 0, 10, 10),  # 上限境界
    ],
)
def test_clamp(x, lo, hi, expected):
    """clamp() は x を閉区間 [lo, hi] に制限する"""
    assert clamp(x, lo, hi) == expected
