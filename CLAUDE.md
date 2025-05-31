# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

```bash
# Install dependencies
pip install monome mido python-rtmidi omegaconf numpy transitions noise aiosc pytest hypothesis pyyaml

# Run tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_control_sender.py

# Run with verbose output
python -m pytest -v tests/

# Run the application
python arc.py

# Run as module
python -c "import arc; arc.start()"
```

## Architecture Overview

### State Machine Design
The application uses a finite state machine (FSM) with the `transitions` library. States and transitions:

- **READY_MODE** → VALUE_SEND_MODE (on first input)
- **VALUE_SEND_MODE** → LAYER_SELECT_MODE (short press)
- **LAYER_SELECT_MODE** → PRESET_SELECT_MODE (long press 0.2s)
- **Any mode** → VALUE_SEND_MODE (button release)
- **Any mode** → DISCONNECT_MODE (device disconnection)

Each mode is implemented as a separate class in `arc/modes/` with `enter()`, `exit()`, and `delta()` methods.

### Service Architecture
Three async services run independently and communicate through the shared Model:

1. **LED Renderer** (`arc/services/renderers/led_renderer.py`)
   - Polls Model state and renders to Arc LEDs
   - Implements caching to avoid redundant updates
   - Maximum brightness: 10 (hardware limitation)

2. **LFO Engine** (`arc/services/lfo/lfo_engine.py`)
   - Runs at 60 FPS (configurable)
   - When LFO is active, ring rotation controls frequency, not value
   - Modulates both values and LED displays

3. **MIDI Sender** (`arc/services/sender/control_sender.py`)
   - Virtual MIDI port: "ArcController OUT"
   - CC mapping: Ring 0-3 on each layer → CC 1-16
   - Supports both 7-bit and 14-bit MIDI

### Model Structure
```
Model
├── layers: List[LayerState]  # 4 layers
│   └── rings: List[RingState]  # 4 rings per layer
│       ├── value: float (0.0-1.0)
│       ├── cc_number: int (1-16)
│       ├── value_style: IValueStyle
│       ├── led_style: ILedStyle
│       └── lfo_style: ILfoStyle
└── active_layer_index: int
```

### Key Implementation Details

1. **Hardware Constants** (`arc/utils/hardware_spec.py`):
   - NUM_ENCS = 4 (number of encoders/rings)
   - LED_PER_RING = 64
   - MAX_LED_LEVEL = 15

2. **Value Styles** determine how encoder input maps to values:
   - `potentiometer`: 0-1 range with stops
   - `infinite`: Continuous rotation
   - `bipolar`: -1 to +1 with center detent
   - `midi_7bit`/`midi_14bit`: Integer MIDI values

3. **Configuration** (`arc/config/config.yaml`):
   - Uses OmegaConf for YAML parsing
   - Presets combine value_style + led_style + lfo_style
   - Configurable: layers, FPS, brightness, logging

4. **Testing**:
   - Uses pytest with Hypothesis for property testing
   - Mock hardware with `DummyGridWrapper`
   - Focus on style behavior and mathematical functions

### Important Patterns

- **Style Factory Pattern**: All styles (LED, value, LFO) are created through factories
- **Async Context Managers**: Services implement `__aenter__`/`__aexit__` for lifecycle
- **Caching**: LED renderer caches to prevent redundant hardware updates
- **State Isolation**: Each mode manages its own UI state independently

### Current Development Tasks (from todo.md)

1. Make long press duration configurable (currently hardcoded 0.2s)
2. MIDI CC channel configuration (currently fixed CC 1-16)
3. Add easing to random LFO style
4. Implement inertia/friction for value changes