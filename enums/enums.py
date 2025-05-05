import enum


class LedStyle(enum.Enum):
    POTENTIOMETER = "potentiometer"
    BIPOLAR = "bipolar"
    DOT = "dot"


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
    RANDOM = "random"
    SINE = "sine"
    SAW = "saw"
    SQUARE = "square"
    TRIANGLE = "triangle"
    PERLIN = "perlin"


class Mode(enum.Enum):
    OPERATE = "operate"
    PRESET = "preset"
