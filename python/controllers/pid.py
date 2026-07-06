from simple_pid import PID

class PIDController:
    def __init__(self, stroke, equilibrium, gains):
        Kp, Ki, Kd = gains
        self._stroke = stroke
        self._equilibrium = equilibrium
        self._pid = PID(Kp, Ki, Kd)
        self._pid.output_limits = (-self._equilibrium, self._stroke-self._equilibrium)
        self._pid.sample_time = 0.05

    def get_command(self, depth_m, depth_setpoint_m):
        self._pid.setpoint = depth_setpoint_m
        cmd = self._pid(depth_m)
        return cmd + self._equilibrium
