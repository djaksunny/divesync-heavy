import gymnasium as gym
import numpy as np
import stable_baselines3 as sb3

class DummyEnv(gym.Env):
    def __init__(self):
        super().__init__()

        observation_low = np.array([0, 0, -2, -0.5], dtype=np.float32)
        observation_high = np.array([2, 2, 2, 0.5], dtype=np.float32)

        action_low = np.array([0], dtype=np.float32)
        action_high = np.array([100], dtype=np.float32)

        self.observation_space = gym.spaces.Box(observation_low, observation_high, (4,), np.float32)
        self.action_space = gym.spaces.Box(action_low, action_high, (1,), np.float32)
        self._step_count = 0
        self._max_steps = 50

    def reset(self, seed=None, options=None):
        self._step_count = 0
        obs = self.observation_space.sample()
        info = {}
        return obs, info

    def step(self, action):
        self._step_count += 1
        obs = self.observation_space.sample()
        reward = 1.0
        terminated = self._step_count >= self._max_steps
        truncated = False
        info = {}
        return obs, reward, terminated, truncated, info

if __name__ == "__main__":
    env = DummyEnv()
    td3 = sb3.TD3("MlpPolicy", env)
    td3.learn(total_timesteps=200)
