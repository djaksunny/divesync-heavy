# Returns random setpoint

import time
import random

class SetpointGenerator:
    def __init__(self, low, high):
        self.depth_target = round(random.uniform(low, high), 4)

    def get_setpoint(self):
        return self.depth_target
