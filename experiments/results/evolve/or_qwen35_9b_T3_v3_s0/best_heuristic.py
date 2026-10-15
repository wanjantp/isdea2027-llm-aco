import numpy as np

def heuristic(dist_m, turn_deg, swath_len_m, energy_left_frac, depot_dist_m, fits):
    eps = 1e-8
    # Feasibility gate: valid moves get 1.0, infeasible get epsilon
    fit_weight = np.where(fits, 1.0, eps)
    
    # Normalize turn to [0, 180] to correctly score 180-degree reversals
    raw_turn = np.fmod(turn_deg, 360.0)
    turn_norm = np.minimum(raw_turn, 360.0 - raw_turn)
    # Score heavily favors 180 turns (cos(180)=-1) and penalizes deviations
    turn_score = 1.0 / (1.0 + 50.0 * (1.0 - np.cos(np.radians(turn_norm))))
    
    # Smooth inverse distance for transit energy
    dist_score = 1.0 / (dist_m + 1.0)
    
    # Dynamic target: shrinks as battery depletes to encourage depot proximity
    target_dist = 3.0 * (1.0 - energy_left_frac)
    lat_score = np.exp(-np.abs(dist_m - target_dist) / 3.0)
    
    return fit_weight * turn_score * dist_score * lat_score
