import logging

import pytest

from enums.enums import LfoStyle
from model.model import Model, RingState


@pytest.fixture(autouse=True)
def clear_log_handlers(monkeypatch):
    # Ensure LOGGER handlers don't interfere across tests
    logger = logging.getLogger("RingState")
    logger.handlers = []
    yield


def test_model_iteration_and_getitem():
    model = Model()
    # Default should have 4 RingState instances
    collected = list(model)
    assert len(collected) == 4
    # __getitem__ should match the internal list
    for idx, ring in enumerate(collected):
        assert model[idx] is ring


def test_model_index_error():
    model = Model()
    with pytest.raises(IndexError):
        _ = model[10]
    with pytest.raises(IndexError):
        _ = list(model)[10]


def test_ringstate_lfo_frequency_clamp():
    rs = RingState()
    # Default within range
    assert rs.lfo_frequency == 0.1
    # Below minimum
    rs.lfo_frequency = -5.0
    assert rs.lfo_frequency == 0.0
    # Above maximum
    rs.lfo_frequency = 100.0
    assert rs.lfo_frequency == 10.0


def test_ringstate_set_lfo_changes_strategy_and_style():
    rs = RingState()
    # Default LFO style and strategy
    assert rs.lfo_style == LfoStyle.STATIC
    assert rs.lfo_strategy.__class__.__name__ == "StaticLfo"
    # Change to a different style
    rs.set_lfo(LfoStyle.SINE)
    assert rs.lfo_style == LfoStyle.SINE
    assert rs.lfo_strategy.__class__.__name__ == "SineLfo"


def test_ringstate_setattr_logs_change(caplog):
    caplog.set_level(logging.INFO, logger="RingState")
    rs = RingState()
    # Change an attribute
    rs.current_value = 0.5
    # Expect a log entry indicating the change
    found = False
    for record in caplog.records:
        if "current_value:" in record.getMessage():
            found = True
            break
    assert found, "Expected log entry for current_value change"
