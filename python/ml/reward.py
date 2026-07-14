import math

def compute_reward(state, w1, w2, w3, tau, action_delta=0.0, w4=0.0):
    error_term = -w1 * state.depth_error_m ** 2
    velocity_term = -w2 * state.velocity_mps ** 2
    surfacing_term = -w3 * math.exp(-state.depth_m / tau)
    action_term = -w4 * (action_delta ** 2)

    return error_term + velocity_term + surfacing_term + action_term
