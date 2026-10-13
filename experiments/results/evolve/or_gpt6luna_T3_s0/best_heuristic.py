import numpy as np

def heuristic(dist_m, turn_deg, swath_len_m, energy_left_frac, depot_dist_m, fits):
    def clean(x, default=0.0):
        x = np.asarray(x, dtype=float)
        return np.maximum(np.nan_to_num(x, nan=default, posinf=1e12, neginf=0.0), 0.0)

    dist = clean(dist_m)
    turn = np.clip(np.nan_to_num(np.asarray(turn_deg, dtype=float),
                                 nan=180.0, posinf=360.0, neginf=0.0), 0.0, 360.0)
    length = clean(swath_len_m)
    depot = clean(depot_dist_m)
    fit = np.clip(np.nan_to_num(np.asarray(fits, dtype=float),
                                nan=0.0, posinf=1.0, neginf=0.0), 0.0, 1.0)
    charge = float(np.clip(np.nan_to_num(energy_left_frac, nan=0.0,
                                         posinf=1.0, neginf=0.0), 0.0, 1.0))

    turn_factor = 1.0 + 0.30 * (turn / 180.0) ** 2
    length_factor = 1.0 + 0.10 * length / (length + 100.0)
    depot_weight = 0.05 + 0.40 * (1.0 - charge) ** 2
    depot_factor = 1.0 + depot_weight * depot / (depot + length + 100.0)
    score = (0.01 + 0.99 * fit) / (
        (1.0 + dist) * turn_factor * length_factor * depot_factor
    )
    return np.maximum(np.nan_to_num(score, nan=1e-300, posinf=1e300,
                                    neginf=1e-300), 1e-300)
