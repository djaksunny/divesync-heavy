def compute_reward(state, w1, w2, w3, tau, action_delta=0.0, w4=0.0):
    error_term = -w1 * state.depth_error_m ** 2
    velocity_term = -w2 * state.velocity_mps ** 2

    return error_term + velocity_term
