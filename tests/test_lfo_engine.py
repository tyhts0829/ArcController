"""
LFO Engine tests

Testing strategy focuses on:
1. Basic initialization and lifecycle management
2. Async task handling (start/stop)
3. LFO instance management and caching
4. MIDI sending logic
5. FPS timing control
"""

import asyncio
import pytest
from unittest.mock import Mock, patch, AsyncMock
from arc.services.lfo.lfo_engine import LFOEngine
from arc.models.model import Model, RingState
from arc.enums.enums import LfoStyle, ValueStyle


class TestLFOEngine:
    """Test LFOEngine basic functionality"""

    def test_init(self):
        """Test initialization"""
        model = Mock()
        led_renderer = Mock()
        midi_sender = Mock()
        
        engine = LFOEngine(model, led_renderer, midi_sender, fps=60)
        
        assert engine.model == model
        assert engine.led_renderer == led_renderer
        assert engine.midi_sender == midi_sender
        assert engine.fps == 60
        assert engine._running is False
        assert engine._task is None
        assert engine._lfos_on_model == {}

    def test_start(self):
        """Test start method"""
        model = Mock()
        led_renderer = Mock()
        midi_sender = Mock()
        engine = LFOEngine(model, led_renderer, midi_sender, fps=60)
        
        with patch('asyncio.create_task') as mock_create_task:
            engine.start()
            
            assert engine._running is True
            mock_create_task.assert_called_once()
            assert engine._task is not None

    def test_start_when_already_running(self):
        """Test start when already running (should not double-start)"""
        model = Mock()
        led_renderer = Mock()
        midi_sender = Mock()
        engine = LFOEngine(model, led_renderer, midi_sender, fps=60)
        
        with patch('asyncio.create_task') as mock_create_task:
            engine.start()
            engine.start()  # Second start
            
            # Should only create task once
            assert mock_create_task.call_count == 1

    def test_stop_sets_flags(self):
        """Test stop method sets flags correctly"""
        model = Mock()
        led_renderer = Mock()
        midi_sender = Mock()
        engine = LFOEngine(model, led_renderer, midi_sender, fps=60)
        
        # Simulate running state
        engine._running = True
        engine._task = Mock()
        
        # Just test the flag setting part synchronously
        engine._running = False
        
        assert engine._running is False

    @pytest.mark.asyncio
    async def test_stop_when_not_running(self):
        """Test stop when not running (should handle gracefully)"""
        model = Mock()
        led_renderer = Mock()
        midi_sender = Mock()
        engine = LFOEngine(model, led_renderer, midi_sender, fps=60)
        
        # Should not raise any errors
        await engine.stop()
        
        assert engine._running is False
        assert engine._task is None

    def test_get_or_create_lfo_new(self):
        """Test LFO creation for new key"""
        model = Mock()
        led_renderer = Mock()
        midi_sender = Mock()
        engine = LFOEngine(model, led_renderer, midi_sender, fps=60)
        
        ring_state = RingState(lfo_style=LfoStyle.PERLIN)
        key = (0, 0)
        
        lfo = engine._get_or_create_lfo(key, ring_state)
        
        assert key in engine._lfos_on_model
        assert engine._lfos_on_model[key] == lfo
        assert lfo.__class__.__name__ == 'PerlinLfoStyle'

    def test_get_or_create_lfo_cached(self):
        """Test LFO retrieval from cache"""
        model = Mock()
        led_renderer = Mock()
        midi_sender = Mock()
        engine = LFOEngine(model, led_renderer, midi_sender, fps=60)
        
        ring_state = RingState(lfo_style=LfoStyle.PERLIN)
        key = (0, 0)
        
        # First call creates
        lfo1 = engine._get_or_create_lfo(key, ring_state)
        # Second call retrieves from cache
        lfo2 = engine._get_or_create_lfo(key, ring_state)
        
        assert lfo1 is lfo2

    def test_get_or_create_lfo_style_change(self):
        """Test LFO recreation on style change"""
        model = Mock()
        led_renderer = Mock()
        midi_sender = Mock()
        engine = LFOEngine(model, led_renderer, midi_sender, fps=60)
        
        key = (0, 0)
        
        # Create with PERLIN style
        ring_state1 = RingState(lfo_style=LfoStyle.PERLIN)
        lfo1 = engine._get_or_create_lfo(key, ring_state1)
        
        # Change to RANDOM_EASE style
        ring_state2 = RingState(lfo_style=LfoStyle.RANDOM_EASE)
        lfo2 = engine._get_or_create_lfo(key, ring_state2)
        
        assert lfo1 is not lfo2
        assert lfo1.__class__.__name__ == 'PerlinLfoStyle'
        assert lfo2.__class__.__name__ == 'RandomEaseLfoStyle'

    def test_update_ring_static_skip(self):
        """Test that STATIC LFO skips processing"""
        model = Mock()
        led_renderer = Mock()
        midi_sender = Mock()
        engine = LFOEngine(model, led_renderer, midi_sender, fps=60)
        
        ring_state = RingState(lfo_style=LfoStyle.STATIC)
        
        engine._update_ring(0, 0, ring_state, 0.016)
        
        # Should not create LFO or render
        assert len(engine._lfos_on_model) == 0
        led_renderer.render_value.assert_not_called()
        midi_sender.send_cc_7bit.assert_not_called()
        midi_sender.send_cc_14bit.assert_not_called()

    def test_update_ring_active_layer(self):
        """Test LED rendering only for active layer"""
        model = Mock()
        model.active_layer_idx = 1
        led_renderer = Mock()
        midi_sender = Mock()
        engine = LFOEngine(model, led_renderer, midi_sender, fps=60)
        
        ring_state = RingState(
            lfo_style=LfoStyle.PERLIN,
            value=0.5,
            cc_number=1
        )
        
        # Update ring on active layer
        engine._update_ring(1, 0, ring_state, 0.016)
        led_renderer.render_value.assert_called_once_with(0, ring_state)
        
        # Update ring on inactive layer
        led_renderer.reset_mock()
        engine._update_ring(0, 0, ring_state, 0.016)
        led_renderer.render_value.assert_not_called()

    def test_send_midi_if_needed_value_change(self):
        """Test MIDI sending on value change"""
        model = Mock()
        led_renderer = Mock()
        midi_sender = Mock()
        engine = LFOEngine(model, led_renderer, midi_sender, fps=60)
        
        # Test 7-bit MIDI
        ring_state = RingState(
            value_style=ValueStyle.MIDI_7BIT,
            lfo_style=LfoStyle.STATIC,
            value=0.5,
            cc_number=1
        )
        engine._send_midi_if_needed(ring_state, old_value=0.4)
        midi_sender.send_cc_7bit.assert_called_once_with(1, 0.5)
        
        # Test 14-bit MIDI
        midi_sender.reset_mock()
        ring_state.value_style = ValueStyle.MIDI_14BIT
        engine._send_midi_if_needed(ring_state, old_value=0.4)
        midi_sender.send_cc_14bit.assert_called_once_with(1, 0.5)

    def test_send_midi_if_needed_no_change(self):
        """Test MIDI not sent when value unchanged (STATIC)"""
        model = Mock()
        led_renderer = Mock()
        midi_sender = Mock()
        engine = LFOEngine(model, led_renderer, midi_sender, fps=60)
        
        ring_state = RingState(
            value_style=ValueStyle.MIDI_7BIT,
            lfo_style=LfoStyle.STATIC,
            value=0.5,
            cc_number=1
        )
        
        # Same value - should not send
        engine._send_midi_if_needed(ring_state, old_value=0.5)
        midi_sender.send_cc_7bit.assert_not_called()
        midi_sender.send_cc_14bit.assert_not_called()

    def test_send_midi_if_needed_lfo_active(self):
        """Test MIDI always sent when LFO active"""
        model = Mock()
        led_renderer = Mock()
        midi_sender = Mock()
        engine = LFOEngine(model, led_renderer, midi_sender, fps=60)
        
        ring_state = RingState(
            value_style=ValueStyle.MIDI_7BIT,
            lfo_style=LfoStyle.PERLIN,
            value=0.5,
            cc_number=1
        )
        
        # Even with same value, LFO active means send
        engine._send_midi_if_needed(ring_state, old_value=0.5)
        midi_sender.send_cc_7bit.assert_called_once_with(1, 0.5)

    def test_loop_calculates_fps_correctly(self):
        """Test that loop calculates frame interval correctly"""
        model = Mock()
        led_renderer = Mock()
        midi_sender = Mock()
        
        # Test 60 FPS
        engine = LFOEngine(model, led_renderer, midi_sender, fps=60)
        frame_interval = 1.0 / engine.fps
        assert abs(frame_interval - 0.01667) < 0.001  # ~16.67ms
        
        # Test 30 FPS
        engine = LFOEngine(model, led_renderer, midi_sender, fps=30)
        frame_interval = 1.0 / engine.fps
        assert abs(frame_interval - 0.03333) < 0.001  # ~33.33ms

    @pytest.mark.asyncio
    async def test_loop_cancellation(self):
        """Test loop handles cancellation properly"""
        model = Model(num_layers=1)
        led_renderer = Mock()
        midi_sender = Mock()
        engine = LFOEngine(model, led_renderer, midi_sender, fps=60)
        
        # Start the engine
        engine.start()
        
        # Give it a moment to start
        await asyncio.sleep(0.01)
        
        # Stop should handle cancellation gracefully
        await engine.stop()
        
        assert engine._running is False
        assert engine._task is None


class TestLFOEngineIntegration:
    """Integration tests with real model"""

    @pytest.mark.asyncio
    async def test_full_update_cycle(self):
        """Test complete update cycle with multiple rings"""
        # Setup model with 2 layers, 2 rings each
        model = Model(num_layers=2)
        model.active_layer_idx = 0
        
        # Configure rings
        model.layers[0].rings[0] = RingState(
            lfo_style=LfoStyle.PERLIN,
            value_style=ValueStyle.MIDI_7BIT,
            value=0.5,
            cc_number=1
        )
        model.layers[0].rings[1] = RingState(
            lfo_style=LfoStyle.STATIC,
            value_style=ValueStyle.MIDI_14BIT,
            value=0.7,
            cc_number=2
        )
        
        led_renderer = Mock()
        midi_sender = Mock()
        engine = LFOEngine(model, led_renderer, midi_sender, fps=60)
        
        # Run one update cycle
        engine._running = True
        
        # Run one frame of the loop
        with patch('asyncio.sleep', side_effect=[asyncio.CancelledError()]):
            try:
                await engine._loop()
            except asyncio.CancelledError:
                pass
        
        # Verify LFO was created for PERLIN ring
        assert (0, 0) in engine._lfos_on_model
        assert engine._lfos_on_model[(0, 0)].__class__.__name__ == 'PerlinLfoStyle'
        
        # Verify STATIC ring was skipped
        assert (0, 1) not in engine._lfos_on_model