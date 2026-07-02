import pygame

class ManualController:
    def __init__(self, stroke):
        pygame.init()
        pygame.joystick.init()

        self._joystick = pygame.joystick.Joystick(0)
        self._joystick.init()

        self._stroke = stroke

    def get_command(self, depth_m=None, depth_setpoint_m=None):
        pygame.event.pump()
        cmd = round(self._stroke * (1 + self._joystick.get_axis(1)) / 2)
        return cmd
