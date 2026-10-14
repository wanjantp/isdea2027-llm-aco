import numpy as np

def heuristic(dist_m, turn_deg, swath_len_m, energy_left_frac, depot_dist_m, fits):
    # Normalized inverse distance (prefer closer transitions)
    inv_dist = 1.0 / (dist_m ** 2 + 1e-6)
    
    # Turn score: heavily reward ~180 deg, moderate for <45 deg, penalize others
    turn_score = np.where(turn_deg <= 45, 2.0, 
                          np.where(np.abs(turn_deg - 180) <= 30, 1.5, 
                                  1.0 - np.minimum(np.abs(turn_deg - 180), 360.0) / 720.0))
    
    # Energy state handling: if swap forced (fits=0), severe penalty; else scale by energy fraction
    fit_penalty = np.where(fits == 0.0, 0.05, 1.0) * (energy_left_frac ** 3.0)
    
    # Depot bonus when energy is low (<35%), prefer candidates ending near depot (depot_dist_m + dist_m approximates total loop)
    depot_bonus = np.where(energy_left_frac < 0.35, 
                          (depot_dist_m + dist_m) / (dist_m + depot_dist_m + 1e-6), 
                          1.0)
    
    return inv_dist * turn_score * fit_penalty * depot_bonus
