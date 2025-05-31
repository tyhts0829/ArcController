import time

import arc

if __name__ == "__main__":
    arc.start()
    print("You can now control Arc without blocking.")
    # do something else
    time.sleep(5)  # Simulate doing something else
    arc.stop()
