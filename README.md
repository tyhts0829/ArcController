# ArcController

A Python-based MIDI controller application for the Monome Arc hardware device. Transform your Arc into a sophisticated MIDI control surface with multiple layers, presets, and visual feedback.

## Features

- **16 Independent MIDI Channels**: 4 layers × 4 rings for comprehensive control
- **Multiple Control Presets**: Different value styles, LED animations, and LFO behaviors
- **Built-in LFO Modulation**: Low Frequency Oscillators with adjustable frequency
- **Real-time LED Visualization**: Multiple display styles for visual feedback
- **Virtual MIDI Port**: Seamless integration with DAWs and music software
- **Async Architecture**: Efficient, non-blocking operation

## Requirements

- Python 3.8+
- Monome Arc hardware device
- Dependencies (install via pip):
  - `monome`
  - `mido`
  - `python-rtmidi`
  - `pyyaml`
  - `numpy`

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/ArcController.git
cd ArcController

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Standalone Application

```bash
python arc.py
```

### As a Python Module

```python
import arc

# Start the controller
arc.start()

# Your code here...

# Stop when done
arc.stop()
```

### Example Scripts

```bash
# Basic example
python examples/start.py

# Manual control example
python examples/manual_control.py
```

## Configuration

Edit `arc/config/config.yaml` to customize:

- **Presets**: Define custom control behaviors
- **Layers**: Set the number of available layers
- **LFO Settings**: Configure update rate (FPS)
- **LED Settings**: Adjust brightness and display options

### Preset Configuration Example

```yaml
presets:
  - name: "Potentiometer"
    value_style: "potentiometer"
    led_style: "potentiometer"
    lfo_style: "static"
  
  - name: "Bipolar"
    value_style: "bipolar"
    led_style: "bipolar"
    lfo_style: "static"
```

## Controls

### Ring Rotation
- **Normal Mode**: Adjust MIDI CC values
- **LFO Active**: Control LFO frequency

### Button Press
- **Short Press**: Switch between layers
- **Long Press (0.2s)**: Change presets
- **Release**: Return to value sending mode

## Architecture

```
arc/
├── app.py              # Main application entry
├── controller/         # Hardware event handling
├── models/            # Data models and state
├── modes/             # Operational modes (state machine)
├── services/          # Core services
│   ├── lfo/          # LFO generation
│   ├── renderers/    # LED rendering
│   └── sender/       # MIDI output
└── config/           # Configuration files
```

## MIDI Integration

1. Start ArcController
2. In your DAW/music software, find the virtual MIDI port "ArcController OUT"
3. Map the 16 CC channels (CC 1-16) to parameters you want to control
4. Use different presets for different control behaviors

## Development

### Running Tests

```bash
python -m pytest tests/
```

### Key Components

- **State Machine**: Clean transitions between operational modes
- **Async Services**: Non-blocking LED rendering, LFO generation, and MIDI output
- **Model-View-Controller**: Separation of concerns for maintainability

## Modes

- **ValueSendMode**: Normal operation for sending MIDI values
- **LayerSelectMode**: Visual layer selection interface
- **PresetSelectMode**: Browse and select control presets
- **ReadyMode**: Initialization when Arc connects
- **DisconnectMode**: Graceful handling of device disconnection

## LED Styles

- **Potentiometer**: Traditional knob-style display
- **Dot**: Single LED indicator
- **Bipolar**: Center-detented display for +/- values
- **Perlin**: Organic, flowing animations

## LFO Styles

- **Static**: No modulation
- **Perlin**: Smooth, organic movement using Perlin noise
- **Random**: Random values with configurable easing

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built for the [Monome Arc](https://monome.org/docs/arc/) hardware
- Inspired by the creative music technology community

## Support

For issues, questions, or contributions, please visit the [GitHub repository](https://github.com/yourusername/ArcController).