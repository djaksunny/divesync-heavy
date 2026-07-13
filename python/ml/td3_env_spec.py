import gymnasium as gym
import numpy as np


class DiveSyncEnvSpec(gym.Env):
    def __init__(self, stroke):
        super().__init__()

        obs_low = np.array([0.0, 0.0, -2.0, -0.5], dtype=np.float32)
        obs_high = np.array([2.0, 2.0, 2.0, 0.5], dtype=np.float32)

        self.observation_space = gym.spaces.Box(obs_low, obs_high, (4,), np.float32)
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
