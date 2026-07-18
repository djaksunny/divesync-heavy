import gymnasium as gym
import numpy as np

OBS_LOW = np.array([0.0, 0.0, -2.0, -0.5], dtype=np.float32)
OBS_HIGH = np.array([2.0, 2.0, 2.0, 0.5], dtype=np.float32)


class DiveSyncEnvSpec(gym.Env):
    def __init__(self, stroke):
        super().__init__()

        self.observation_space = gym.spaces.Box(OBS_LOW, OBS_HIGH, (4,), np.float32)
        self.action_space = gym.spaces.Box(
            np.array([0.0], dtype=np.float32),
            np.array([stroke], dtype=np.float32),
            (1,),
            np.float32,
        )

    def reset(self, seed=None, options=None):
        return self.observation_space.sample(), {}

    def step(self, action):
        obs = self.observation_space.sample()
        return obs, 0.0, False, False, {}
