# Returns a value for square wave given low, high, period

import time

class SquareWaveController:
    def __init__(self, low, high, period):
        self._low = low
        self._high = high
        self._period = period

        self._last_switch = time.time()
        self._is_high = True # default high

    def get_command(self, state=None):
        # state unused here, but kept for unified interface across controllers
        if time.time() - self._last_switch >= self._period / 2:
            self._is_high = not self._is_high
            self._last_switch = time.time()

        return self._high if self._is_high else self._low
