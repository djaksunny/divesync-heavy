import math

def compute_reward(state, w1, w2, w3, tau):
    error_term = -w1 * state.depth_error_m ** 2
    velocity_term = -w2 * state.velocity_mps ** 2
    surfacing_term = -w3 * math.exp(-state.depth_m / tau)

    return error_term + velocity_term + surfacing_term