import numpy as np
def heuristic(dist_m, turn_deg, swath_len_m, energy_left_frac, depot_dist_m, fits):
    return (1.0 / (dist_m + 1.0)) ** 3
