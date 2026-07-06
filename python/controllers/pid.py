from simple_pid import PID

class PIDController:
    def __init__(self, stroke, gains):
        Kp, Ki, Kd = gains
        self._stroke = stroke
        self._pid = PID(Kp, Ki, Kd)
        self._pid.output_limits = (0, stroke)
        self._pid.sample_time = 0.05

    def get_command(self, depth_m, depth_setpoint_m):
        self._pid.setpoint = depth_setpoint_m
        cmd = self._pid(depth_m)
        return cmd
