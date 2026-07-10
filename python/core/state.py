import time

class State:
    def __init__(self, velocity_window=9):
        self.time_s = 0.0

        self.depth_m = 0.0
        self.depth_setpoint_m = 0.0
        self.depth_error_m = 0.0
        self.velocity_mps = 0.0

        self._last_time_s = None
        self._last_depth_m = None

        self._velocity_window = []
        self._VELOCITY_LIMIT = velocity_window  # odd number recommended for clean median

        self.state_csv = None

    @staticmethod
    def _fmt(x, digits=4):
        """Format a value for CSV, safely handling None."""
        return f"{round(x, digits)}" if x is not None else ""

    def update(self, pro):
        self.time_s = pro.time_s
        self.depth_m = pro.depth_filtered_m
        self.depth_setpoint_m = pro.depth_setpoint_m

        # Calculate depth error (only if we have both a setpoint and a depth reading)
        if self.depth_setpoint_m is not None and self.depth_m is not None:
            self.depth_error_m = self.depth_setpoint_m - self.depth_m
        else:
            self.depth_error_m = None

        # Calculate raw vertical velocity
        if self._last_time_s is None or self.depth_m is None or self._last_depth_m is None:
            velocity_raw = 0.0
        else:
            dt = self.time_s - self._last_time_s

            if dt > 0:
                velocity_raw = (self.depth_m - self._last_depth_m) / dt
            else:
                velocity_raw = 0.0

        # Median filter on velocity to reject sensor-quantization jitter
        self._velocity_window.append(velocity_raw)

        if len(self._velocity_window) > self._VELOCITY_LIMIT:
            self._velocity_window.pop(0)

        sorted_window = sorted(self._velocity_window)
        mid = len(sorted_window) // 2
        self.velocity_mps = sorted_window[mid]

        # Store current values for next update
        self._last_time_s = self.time_s
        self._last_depth_m = self.depth_m

        self.state_csv = (
            f"{self._fmt(self.time_s, 3)},"
            f"{self._fmt(self.depth_m)},"
            f"{self._fmt(self.depth_setpoint_m)},"
            f"{self._fmt(self.depth_error_m)},"
            f"{self._fmt(self.velocity_mps)}"
        )
