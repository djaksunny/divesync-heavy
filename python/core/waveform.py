# Returns a value for square wave given low, high, period

import time

class SquareWaveGenerator:
    def __init__(self, low, high, period):
        self._low = low
        self._high = high
        self._period = period

        self._last_switch = time.time()
        self._is_high = True # default high

    def return_value(self):
        if time.time() - self._last_switch >= self._period:
            # If high, flip and return low
            if self._is_high:
                self._is_high = not self._is_high
                return self._low
            
            # If low, flip and return high
            self._is_high = not self._is_high
            return self._high
        
        # Return value, not time to switch
        return self._low if self._is_high else self._high
