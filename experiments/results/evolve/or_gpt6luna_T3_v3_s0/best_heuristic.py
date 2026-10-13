import numpy as np

def heuristic(dist_m, turn_deg, swath_len_m, energy_left_frac, depot_dist_m, fits):
    def clean(x, nan, pos, neg):
        return np.nan_to_num(np.asarray(x, dtype=float), nan=nan,
                             posinf=pos, neginf=neg)

    dist = np.maximum(clean(dist_m, 1e12, 1e12, 0.0), 0.0)
    turn = np.clip(clean(turn_deg, 180.0, 360.0, 0.0), 0.0, 360.0)
    length = np.maximum(clean(swath_len_m, 1e12, 1e12, 0.0), 0.0)
    depot = np.maximum(clean(depot_dist_m, 1e12, 1e12, 0.0), 0.0)
    feasible = clean(fits, 0.0, 0.0, 0.0) >= 0.5
    charge = float(np.clip(np.nan_to_num(energy_left_frac, nan=0.0,
                                         posinf=1.0, neginf=0.0), 0.0, 1.0))

    score = 1.0 / (1.0 + dist)
    score *= 1.0 / (1.0 + turn / 180.0)
    score *= 1.0 / (1.0 + length / (1.0 + np.median(length)))
    score *= np.exp(-2.0 * (1.0 - charge) * depot / (1.0 + depot))
    score *= np.where(feasible, 1.0, 0.01)
    return np.maximum(np.nan_to_num(score, nan=1e-12, posinf=1.0,
                                    neginf=1e-12), 1e-12)
