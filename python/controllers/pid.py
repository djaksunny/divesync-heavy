from simple_pid import PID

class PIDController:
    def __init__(self, inner_gains, outer_gains=None):
        Kp, Ki, Kd = inner_gains
        self._inner = PID(Kp, Ki, Kd)
        self._inner.output_limits = (-255, 255)
        self._inner.sample_time = 0.05

        self._outer = None
        if outer_gains:
            Kp_o, Ki_o, Kd_o = outer_gains
            self._outer = PID(Kp_o, Ki_o, Kd_o)
            self._outer.sample_time = 0.05

    def get_command(self, actuator_mm=None, actuator_setpoint_mm=None, depth_m=None, depth_setpoint_m=None):
        if self._outer and depth_setpoint_m is not None:
            self._outer.setpoint = depth_setpoint_m
            actuator_setpoint_mm = self._outer(depth_m)
            
        elif actuator_setpoint_mm is None:
            raise ValueError(
                "Cannot compute PID command: Inner loop actuator_setpoint_mm is required"
            )

        self._inner.setpoint = actuator_setpoint_mm
        pwm = round(self._inner(actuator_mm))
        return f"U:{pwm}\n"
