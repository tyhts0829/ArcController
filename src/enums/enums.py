import enum


class LedStyle(enum.Enum):
    POTENTIOMETER = "potentiometer"
    BIPOLAR = "bipolar"
    DOT = "dot"
    PERLIN = "perlin"


class ValueStyle(enum.Enum):
    # 0.0 to 1
    LINEAR = "linear"
    # -0.5 to 0.5
    BIPOLAR = "bipolar"
    # -inf to inf
    INFINITE = "infinite"
    # 0 to 127
    MIDI_7BIT = "midi_7_bit"
    # 0 to 16383
    MIDI_14BIT = "midi_14_bit"


class LfoStyle(enum.Enum):
    STATIC = "static"
    SINE = "sine"
    SAW = "saw"
    SQUARE = "square"
    TRIANGLE = "triangle"
    PERLIN = "perlin"
    RANDOM_EASE = "random_ease"


class Mode(enum.Enum):
    READY_MODE = "ready_mode"
    PRESET_SELECT_MODE = "preset_select_mode"
    LAYER_SELECT_MODE = "layer_select_mode"
    VALUE_SEND_MODE = "value_send_mode"
    DISCONNECT_MODE = "disconnect_mode"
