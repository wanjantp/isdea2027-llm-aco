import numpy as np

def heuristic(dist_m, turn_deg, swath_len_m, energy_left_frac, depot_dist_m, fits):
    # Inverse-square distance penalty: strongly favors adjacent swaths (small dist)
    dist_term = 1.0 / (dist_m + 1e-6)**2
    
    # Linear turn cost: 0 is optimal (continuation), 180 is sharp turn, 360 is full circle waste
    turn_term = 1.0 + 0.0 * turn_deg
    
    # Safety multiplier: 
    # If 'fits' is true (1.0), score is boosted by energy_left_frac (encourage efficiency).
    # If 'fits' is false (0.0), score drops to a small epsilon proportional to energy_left_frac 
    # (discourage infeasible moves when battery is low, allow them when plenty remains).
    safety_term = fits + (1.0 - fits) * 1e-2 + (1.0 - fits) * 0.9 * energy_left_frac
    
    return dist_term * turn_term * safety_term
