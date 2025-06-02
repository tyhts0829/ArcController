import time

import arc

if __name__ == "__main__":
    # Test the new functionality: enable MIDI, disable OSC
    arc.start(midi=False, osc=True)
    print("Arc started with MIDI enabled and OSC disabled.")
    # do something else
    time.sleep(5)  # Simulate doing something else
    arc.stop()
