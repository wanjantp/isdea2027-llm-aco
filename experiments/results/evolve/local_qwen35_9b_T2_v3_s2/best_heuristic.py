import numpy as np

def heuristic(dist_m, turn_deg, swath_len_m, energy_left_frac, depot_dist_m, fits):
    dist_score = np.exp(-dist_m / 5.0) * (1.0 + dist_m)
    turn_norm = (turn_deg % 360.0) * np.pi / 180.0 - np.pi / 2.0
    turn_penalty = 1.0 - np.tanh(turn_norm)
    length_score = swath_len_m / (swath_len_m + 1e-6)
    return dist_score * turn_penalty * length_score
