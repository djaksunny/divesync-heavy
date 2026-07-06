import pygame
import random

class ManualController:
    def __init__(self, stroke, actuator_equilibrium):
        pygame.init()
        pygame.joystick.init()

        self._joystick = pygame.joystick.Joystick(0)
        self._joystick.init()

        self._stroke = stroke
        self.actuator_equilibrium = actuator_equilibrium

        self.depth_target = random.uniform(0.2, 0.8)

    def get_command(self):
        pygame.event.pump()

        axis = self._joystick.get_axis(1)

        if abs(axis) < 0.1:
            axis = 0.0

        if axis >= 0:
            available_range = self._stroke - self.actuator_equilibrium
            output = self.actuator_equilibrium + (axis * available_range)
        else:
            available_range = self.actuator_equilibrium
            output = self.actuator_equilibrium + (axis * available_range)

        return output