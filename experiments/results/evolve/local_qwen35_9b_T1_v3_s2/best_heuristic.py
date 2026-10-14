import numpy as np

def heuristic(dist_m, turn_deg, swath_len_m, energy_left_frac, depot_dist_m, fits):
    eps = 1e-6
    safe_horizon = 50.0 * (energy_left_frac ** 2) + 8.0
    d_safe = np.maximum(dist_m - safe_horizon, eps)
    safety_term = 1.0 / d_safe
    dist_reward = 1.0 / ((dist_m + eps) ** 3)
    turn_penalty = 1.0 / (1.0 + turn_deg * 0.13)
    return safety_term * dist_reward * turn_penalty * 125.0
