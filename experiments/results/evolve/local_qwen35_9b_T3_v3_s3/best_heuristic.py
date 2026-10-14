import numpy as np

def heuristic(dist_m, turn_deg, swath_len_m, energy_left_frac, depot_dist_m, fits):
    eps = 1e-4
    
    # Steep sigmoid to sharply favor ideal ~180° turns over others
    turn_score = 1.0 / (1.0 + np.exp(3.0 * (turn_deg - 180.0)))
    
    # Exponential suppression for infeasible candidates combined with linear energy buffer reward
    safe_term = np.exp(-5.0 * (1.0 - fits)) + 0.3 * energy_left_frac
    
    # Bounded inverse distance to attract paths ending near the depot when risky
    depot_influence = 1.0 / np.minimum(depot_dist_m + 50.0, 200.0)
    
    # Inverse-square penalty for transit distance to favor adjacent swaths
    dist_score = 1.0 / ((dist_m + eps) ** 2)
    
    return dist_score * turn_score * safe_term * (0.3 + depot_influence)
