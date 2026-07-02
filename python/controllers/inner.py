from simple_pid import PID

class InnerPIDController:
    def __init__(self, gains):
        Kp, Ki, Kd = gains
        self._pid = PID(Kp, Ki, Kd)
        self._pid.output_limits = (-255, 255)
        self._pid.sample_time = 0.05

    def get_command(self, actuator_mm, actuator_setpoint_mm):
        if actuator_setpoint_mm is None:
            raise ValueError(
                "Cannot compute PID command: Inner loop actuator_setpoint_mm is required"
            )

        self._pid.setpoint = actuator_setpoint_mm
        pwm = round(self._pid(actuator_mm))
        return f"U:{pwm}\n"
