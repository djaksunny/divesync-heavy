# Processes telemetry object to contain processed depth (median filtering) and actuator displacement (scaled to mm)

class Processor:
    def __init__(self):
        self._window = []
        self._LIMIT = 15

        self.depth_filtered_m = None
        self.depth_setpoint_m = None
        self.actuator_mm = None
        self.actuator_setpoint_mm = None
        self.processed_csv = None

    def process(self, tel, depth_setpoint_m=None, actuator_setpoint_mm=None):
        # Update window
        self._window.append(tel.depth_m)

        if len(self._window) > self._LIMIT:
            self._window.pop(0)

        # Median filter
        sorted_window = sorted(self._window)

        mid = len(sorted_window) // 2
        self.depth_filtered_m = sorted_window[mid]

        # Actuator units conversion
        self.actuator_mm = round(tel.actuator_raw * 50 / 4095, 3)

        # Update setpoints
        self.depth_setpoint_m = depth_setpoint_m
        self.actuator_setpoint_mm = actuator_setpoint_mm  

        # Saves CSV for logger
        self.processed_csv = f"{self.depth_filtered_m},{self.depth_setpoint_m},{self.actuator_mm},{self.actuator_setpoint_mm}"
