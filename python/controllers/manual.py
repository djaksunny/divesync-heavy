import pygame

class ManualController:
    def __init__(self):
        pygame.init()
        pygame.joystick.init()

        self._joystick = pygame.joystick.Joystick(0)
        self._joystick.init()

    def get_command(self, actuator_mm=None, actuator_setpoint_mm=None, depth_m=None, depth_setpoint_m=None):
        pygame.event.pump()
        pwm = round(255 * self._joystick.get_axis(1))
        return f"U:{pwm}\n"
