import os
import numpy as np
import joblib
from stable_baselines3 import TD3

from ml.reward import compute_reward
from ml.td3_env_spec import DiveSyncEnvSpec


class RLController:
    def __init__(self, stroke, w1=1.0, w2=0.1, w3=2.0, tau=0.3,
                 exploration_sigma=0.1, gradient_steps=200, batch_size=100,
                 model_dir="python/ml"):
        self._stroke = float(stroke)
        self._w1, self._w2, self._w3, self._tau = w1, w2, w3, tau
        self._exploration_sigma = exploration_sigma
        self._gradient_steps = gradient_steps
        self._batch_size = batch_size

        self._model_path = f"{model_dir}/td3_model"
        self._buffer_path = f"{model_dir}/td3_replay_buffer.pkl"
        self._warmstart_path = f"{model_dir}/td3_warmstart"

        env = DiveSyncEnvSpec(stroke)

        if os.path.exists(self._model_path + ".zip"):
            self.model = TD3.load(self._model_path, env=env)
            if os.path.exists(self._buffer_path):
                self.model.load_replay_buffer(self._buffer_path)
            print("[RL] Loaded existing TD3 model + replay buffer")
        else:
            self.model = TD3.load(self._warmstart_path, env=env)
            print("[RL] Loaded BC warm-start TD3 model (first RL dive)")

        from stable_baselines3.common.logger import configure
        self.model.set_logger(configure(None, []))

        self._prev_state_vec = None
        self._prev_action_norm = None

    @staticmethod
    def _state_to_array(state):
        return np.array([
            state.depth_m,
            state.depth_setpoint_m,
            state.depth_error_m,
            state.velocity_mps,
        ], dtype=np.float32)

    def get_command(self, state):
        state_vec = self._state_to_array(state)

        if self._prev_state_vec is not None:
            reward = compute_reward(state, self._w1, self._w2, self._w3, self._tau)
            self.model.replay_buffer.add(
                self._prev_state_vec.reshape(1, -1),
                state_vec.reshape(1, -1),
                self._prev_action_norm.reshape(1, -1),
                np.array([reward], dtype=np.float32),
                np.array([False]),
                [{}],
            )

        import torch
        state_tensor = torch.tensor(state_vec.reshape(1, -1), dtype=torch.float32)

        with torch.no_grad():
            normalized_action = self.model.policy.actor(state_tensor).numpy()[0]

        noise = np.random.normal(0, self._exploration_sigma, size=normalized_action.shape).astype(np.float32)
        normalized_action = np.clip(normalized_action + noise, -1.0, 1.0)

        action_mm = self._stroke * (normalized_action[0] + 1.0) / 2.0
        action_mm = float(max(0.0, min(self._stroke, action_mm)))

        self._prev_state_vec = state_vec
        self._prev_action_norm = normalized_action

        return action_mm

    def finalize(self, last_state=None):
        if self._prev_state_vec is not None:
            if last_state is not None:
                final_vec = self._state_to_array(last_state)
                reward = compute_reward(last_state, self._w1, self._w2, self._w3, self._tau)
            else:
                final_vec = self._prev_state_vec
                reward = 0.0

            self.model.replay_buffer.add(
                self._prev_state_vec.reshape(1, -1),
                final_vec.reshape(1, -1),
                self._prev_action_norm.reshape(1, -1),
                np.array([reward], dtype=np.float32),
                np.array([True]),
                [{}],
            )

        if self.model.replay_buffer.size() >= self._batch_size:
            self.model.train(gradient_steps=self._gradient_steps, batch_size=self._batch_size)
        else:
            print("[RL] Not enough transitions yet to train — skipping update this dive")

        self.model.save(self._model_path)
        self.model.save_replay_buffer(self._buffer_path)
        print(f"[RL] Saved model + buffer ({self.model.replay_buffer.size()} transitions)")
