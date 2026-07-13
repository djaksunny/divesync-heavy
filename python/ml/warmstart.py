import numpy as np
import torch
import joblib
from stable_baselines3 import TD3

from train_bc import BCModel
from td3_env_spec import DiveSyncEnvSpec


def convert_bc_to_td3(bc_weights_path, y_scaler_path, stroke, out_path):
    bc = BCModel()
    bc.load_state_dict(torch.load(bc_weights_path))
    bc.eval()

    y_scaler = joblib.load(y_scaler_path)
    y_scale = float(y_scaler.scale_[0])
    y_mean = float(y_scaler.mean_[0])

    env = DiveSyncEnvSpec(stroke)
    model = TD3("MlpPolicy", env, policy_kwargs=dict(net_arch=[64, 64]))

    actor = model.policy.actor

    # BCModel's layer3 has no activation; SB3's actor ends in Tanh.
    # A,B rescale the final linear layer so its pre-tanh output lands
    # near BC's original normalized action, in tanh's near-linear region.
    A = 2.0 * y_scale / stroke
    B = 2.0 * y_mean / stroke - 1.0

    with torch.no_grad():
        actor.mu[0].weight.copy_(bc.layer1.weight)
        actor.mu[0].bias.copy_(bc.layer1.bias)
        actor.mu[2].weight.copy_(bc.layer2.weight)
        actor.mu[2].bias.copy_(bc.layer2.bias)
        actor.mu[4].weight.copy_(bc.layer3.weight * A)
        actor.mu[4].bias.copy_(bc.layer3.bias * A + B)

    model.policy.actor_target.load_state_dict(model.policy.actor.state_dict())

    model.save(out_path)
    print(f"Saved warm-started TD3 model to {out_path}.zip")


if __name__ == "__main__":
    convert_bc_to_td3(
        bc_weights_path="python/ml/bc_model_weights.pt",
        y_scaler_path="python/ml/y_scaler.pkl",
        stroke=100.0,
        out_path="python/ml/td3_warmstart",
    )
