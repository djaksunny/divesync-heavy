import shutil
import time

import numpy as np
from stable_baselines3.common.save_util import load_from_pkl, save_to_pkl

from ml.reward import compute_reward
from ml.td3_env_spec import OBS_LOW, OBS_HIGH


class _RawState:
    __slots__ = ("depth_m", "depth_error_m", "velocity_mps")

    def __init__(self, depth_m, depth_error_m, velocity_mps):
        self.depth_m = depth_m
        self.depth_error_m = depth_error_m
        self.velocity_mps = velocity_mps


def relabel(buffer_path, w1=10.0, w2=20.0, w3=2.0, w4=5.0, tau=0.3):
    """Recompute every stored transition's reward under the current
    compute_reward(), using the raw state recovered from the buffer's
    normalized next_observations. Lets reward.py change without leaving
    old transitions labeled under a stale reward function."""
    buf = load_from_pkl(buffer_path)
    n = buf.buffer_size if buf.full else buf.pos

    backup_path = f"{buffer_path}.bak-{time.strftime('%Y%m%d-%H%M%S')}"
    shutil.copy(buffer_path, backup_path)
    print(f"[relabel] Backed up buffer to {backup_path}")

    next_obs = buf.next_observations[:n, 0, :]
    raw = (next_obs + 1.0) / 2.0 * (OBS_HIGH - OBS_LOW) + OBS_LOW
    depth_m, error_m, velocity_mps = raw[:, 0], raw[:, 2], raw[:, 3]

    old_rewards = buf.rewards[:n, 0].copy()
    new_rewards = np.empty(n, dtype=np.float32)
    for i in range(n):
        s = _RawState(depth_m[i], error_m[i], velocity_mps[i])
        new_rewards[i] = compute_reward(s, w1, w2, w3, tau, action_delta=0.0, w4=0.0)

    buf.rewards[:n, 0] = new_rewards
    save_to_pkl(buffer_path, buf)

    print(f"[relabel] Relabeled {n} transitions")
    print(f"[relabel] old reward: mean={old_rewards.mean():.4f} std={old_rewards.std():.4f}")
    print(f"[relabel] new reward: mean={new_rewards.mean():.4f} std={new_rewards.std():.4f}")


if __name__ == "__main__":
    relabel("python/ml/td3_replay_buffer.pkl")
