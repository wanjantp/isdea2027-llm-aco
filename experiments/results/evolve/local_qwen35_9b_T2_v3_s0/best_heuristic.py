import numpy as np

def heuristic(dist_m, turn_deg, swath_len_m, energy_left_frac, depot_dist_m, fits):
    eps = 1e-6
    
    # Reward for short transit (adjacent swaths) using inverse square to favor proximity
    dist_score = 1.0 / (dist_m ** 2 + eps)
    
    # Reward swath length linearly but normalized to prevent saturation
    len_score = swath_len_m / (swath_len_m + eps)
    
    # Explicit penalty for sharp turns; cost grows quadratically with angle deviation from ideal
    turn_penalty = 1.0 + (turn_deg ** 2) / (90.0 ** 2 + eps)
    
    return dist_score * len_score / turn_penalty
