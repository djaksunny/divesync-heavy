from simple_pid import PID

class InnerPIDController:
    def __init__(self, gains, deadband=None):
        Kp, Ki, Kd = gains
        self._deadband = deadband if deadband else 0
        self._max_output = 255 - self._deadband

        self._pid = PID(Kp, Ki, Kd)
        self._pid.output_limits = (-self._max_output, self._max_output)
        self._pid.sample_time = 0.05

    def get_command(self, actuator_mm, actuator_setpoint_mm):
        if actuator_setpoint_mm is None:
            raise ValueError(
                "Cannot compute PID command: Inner loop actuator_setpoint_mm is required"
            )

        self._pid.setpoint = actuator_setpoint_mm
        raw = self._pid(actuator_mm)

        if abs(raw) < 0.5:
            pwm = 0
        else:
            sign = 1 if raw > 0 else -1
            magnitude = min(abs(raw), self._max_output)
            pwm = sign * (
                self._deadband + magnitude * (255 - self._deadband) / self._max_output
            )

        pwm = round(pwm)
        return f"U:{pwm}\n"
