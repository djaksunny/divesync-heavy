from simple_pid import PID
import time

class PIDController:
    def __init__(self, Kp, Ki, Kd, low_mm, high_mm, period_s):
        self._pid = PID(Kp, Ki, Kd)
        self._pid.output_limits = (-255, 255)
        self._pid.sample_time = 0.05

        self._low_mm = low_mm
        self._high_mm = high_mm
        self._period_s = period_s
        self._last_switch_time = time.time()
        self._is_high = False

        self.current_setpoint = low_mm  # exposed for logging

    def _get_setpoint(self):
        if time.time() - self._last_switch_time >= self._period_s:
            self._is_high = not self._is_high
            self._last_switch_time = time.time()
        return self._high_mm if self._is_high else self._low_mm

    def set_state(self, actuator_mm):
        self._actuator_mm = actuator_mm

    def get_command(self):
        self.current_setpoint = self._get_setpoint()
        self._pid.setpoint = self.current_setpoint
        pwm = round(self._pid(self._actuator_mm))
        return f"U:{pwm}\n"
