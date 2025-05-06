import asyncio

import pytest

from controller.lfo_engine import LfoEngine
from enums.enums import LfoStyle


class DummyState:
    def __init__(self):
        self.lfo_style = LfoStyle.STATIC
        # LFO strategy not used for STATIC
        self.lfo_strategy = None
        self.current_value = 0.0


class DummyModel:
    def __init__(self, states):
        self._states = states

    def __iter__(self):
        return iter(self._states)


class DummyRenderer:
    def __init__(self, engine):
        self.engine = engine
        self.calls = []

    def render(self, ring_number, ring_state):
        # Record render calls
        self.calls.append((ring_number, ring_state))
        # After first frame, stop the loop
        self.engine._running = False


@pytest.mark.asyncio
async def test_loop_renders_once():
    state = DummyState()
    model = DummyModel([state])
    engine = LfoEngine(model, led_renderer=None, fps=10)
    renderer = DummyRenderer(engine)
    engine.led_renderer = renderer

    # Run one iteration of the loop
    engine._running = True
    await engine._loop()

    # Should have rendered exactly once for ring 0
    assert renderer.calls == [(0, state)]


@pytest.mark.asyncio
async def test_stop_cancels_task():
    state = DummyState()
    model = DummyModel([state])
    engine = LfoEngine(model, led_renderer=DummyRenderer(None), fps=10)

    # Start the engine task
    engine.start()
    # Give control back to loop to start the task
    await asyncio.sleep(0)

    # Stop the engine and give cancellation time
    engine.stop()
    await asyncio.sleep(0)

    # After stop, the engine should not be running
    assert engine._running is False
    # The task should be cancelled or finished
    assert engine._task is not None
    assert engine._task.cancelled() or engine._task.done()
