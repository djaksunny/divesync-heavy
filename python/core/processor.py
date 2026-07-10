# Processes telemetry object to contain processed depth (median filtering) and actuator displacement (scaled to mm), along with setpoints
# format: time_s, actuator_mm, actuator_setpoint_mm, depth_filtered_m, depth_setpoint_m, motor_cmd

class Processor:
    def __init__(self, stroke):
        self._window = []
        self._LIMIT = 15

        self._stroke = stroke

        self.time_s = None
        self.depth_filtered_m = None
        self.actuator_setpoint_mm = None
        self.actuator_mm = None
        self.depth_setpoint_m = None
        self.motor_cmd = None
        self.processed_csv = None

    def process_depth(self, tel):
        # Update window
        self._window.append(tel.depth_m)

        if len(self._window) > self._LIMIT:
            self._window.pop(0)

        # Median filter
        sorted_window = sorted(self._window)

        mid = len(sorted_window) // 2
        self.depth_filtered_m = sorted_window[mid]

        # Actuator units conversion (doesn't depend on controller output)
        self.actuator_mm = round(tel.actuator_raw * self._stroke / 4095, 3)

        # Update time
        self.time_s = tel.time_ms / 1000

        # Stash tel for use in process_actuator (need motor_cmd for csv)
        self._tel = tel

    def process_actuator(self, actuator_setpoint_mm, depth_setpoint_m=None):
        # Update setpoints
        self.actuator_setpoint_mm = actuator_setpoint_mm
        self.depth_setpoint_m = depth_setpoint_m
        self.motor_cmd = self._tel.motor_cmd * 12 / 255

        # Saves CSV for logger
        self.processed_csv = f"{self.time_s},{self.actuator_mm},{self.actuator_setpoint_mm},{self.depth_filtered_m},{self.depth_setpoint_m},{self.motor_cmd}"

    def process(self, tel, actuator_setpoint_mm, depth_setpoint_m=None):
        # Kept for backward compatibility if anything still calls the old single-shot method
        self.process_depth(tel)
        self.process_actuator(actuator_setpoint_mm, depth_setpoint_m)
