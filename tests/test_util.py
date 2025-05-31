import pytest
from hypothesis import assume, given
from hypothesis import strategies as st
from arc.utils.util import clamp


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


# ----------------------------------------------------------------------
# Property‑based tests for clamp() to make future ranges robust
# ----------------------------------------------------------------------


# Strategy: generate a sorted (lo, hi) pair and an arbitrary x
floats = st.floats(
    min_value=-1e9,
    max_value=1e9,
    allow_nan=False,
    allow_infinity=False,
    width=32,
)


@given(x=floats, bounds=st.tuples(floats, floats))
def test_clamp_within_bounds_property(x, bounds):
    """出力が必ず [lo, hi] に入るという不変条件を検証"""
    lo, hi = bounds
    assume(lo <= hi)  # discard cases where bounds are invalid

    out = clamp(x, lo, hi)

    assert lo <= out <= hi


@given(x=floats)
def test_clamp_identity_property(x):
    """lo ≤ x ≤ hi のとき clamp(x) == x になるかを検証"""
    lo = x - 1.0
    hi = x + 1.0

    assert clamp(x, lo, hi) == x


def test_clamp_invalid_bounds_raises():
    """lo > hi の場合は ValueError を送出することを期待"""
    with pytest.raises(ValueError):
        clamp(0, 10, 0)
