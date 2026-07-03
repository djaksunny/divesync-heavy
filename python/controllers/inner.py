from simple_pid import PID

class InnerPIDController:
    def __init__(self, gains, deadband=None):
        Kp, Ki, Kd = gains
        if deadband:
            self._deadband = deadband
        else:
            self._deadband = 0
        self._pid = PID(Kp, Ki, Kd)
        self._pid.output_limits = (-255+self._deadband, 255-self._deadband)
        self._pid.sample_time = 0.05

    def get_command(self, actuator_mm, actuator_setpoint_mm):
        if actuator_setpoint_mm is None:
            raise ValueError(
                "Cannot compute PID command: Inner loop actuator_setpoint_mm is required"
            )

        self._pid.setpoint = actuator_setpoint_mm
        pwm = round(self._pid(actuator_mm))
        if pwm >= -2 and pwm <= 2:
            pwm = 0
        elif pwm > 2:
            pwm += self._deadband
        else:
            pwm -= self._deadband
        return f"U:{pwm}\n"
