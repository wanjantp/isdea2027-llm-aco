import numpy as np

def heuristic(dist_m, turn_deg, swath_len_m, energy_left_frac, depot_dist_m, fits):
    # Use a fixed global bound for normalization to ensure consistency regardless of input batch size
    global_max_len = 10000.0 
    length_normalized = swath_len_m / global_max_len
    
    # Strict feasibility check: only candidates fitting in current battery get full score; others heavily penalized
    capacity_proxy = 2.0 * (1.0 - energy_left_frac) + 1e-6
    estimated_load = dist_m + swath_len_m + depot_dist_m
    feasibility_score = np.where(estimated_load <= capacity_proxy, 1.0, 1e-9)
    
    # Smooth quadratic turn alignment favoring ~180° (adjacent) or ~0° turns to minimize turning cost
    turn_diff_180 = np.abs(turn_deg - 180.0)
    turn_diff_0 = np.abs(turn_deg - 0.0)
    turn_alignment = 1.0 / (1.0 + (turn_diff_180**2 + turn_diff_0**2) / 50000.0)
    
    # Distance decay balances travel efficiency without over-penalizing short hops
    transit_efficiency = np.exp(-dist_m * 0.0015) * (1.0 / (dist_m ** 2 + 1.0))
    
    # Adaptive depot attraction: stronger pull when battery is low, scaled by normalized swath length importance
    energy_factor = (1.0 - energy_left_frac) ** 2.5
    depot_proximity = energy_factor * (length_normalized / (depot_dist_m ** 2 + 1.0)) + 0.04
    
    return feasibility_score * transit_efficiency * turn_alignment * depot_proximity
