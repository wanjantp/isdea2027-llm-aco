import numpy as np

def heuristic(dist_m, turn_deg, swath_len_m, energy_left_frac, depot_dist_m, fits):
    # Penalize non-adjacent hops with a steep quadratic term around 5m threshold
    dist_term = ((dist_m - 5.0) / 10.0) ** 2
    
    # Penalize deviation from ideal 180-degree reversal; normalize by swath length to scale cost
    rad_turn = np.deg2rad(turn_deg)
    turn_term = (np.abs(rad_turn - np.pi) / np.pi) * (1.0 / (swath_len_m + 1e-6))
    
    # Combine penalties multiplicatively to enforce both constraints simultaneously
    combined_penalty = dist_term + turn_term + 1e-3
    
    # Invert and scale to ensure strictly positive finite floats with reasonable magnitude
    return 1.0 / (combined_penalty * np.pi)
