import numpy as np

def heuristic(dist_m, turn_deg, swath_len_m, energy_left_frac, depot_dist_m, fits):
    return 1.0 / (dist_m + 0.1 * turn_deg + 1.0) ** 2.0 * np.where(fits > 0.5, 1.0, 0.2)
