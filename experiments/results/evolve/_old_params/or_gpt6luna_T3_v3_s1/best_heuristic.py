import numpy as np

def heuristic(dist_m, turn_deg, swath_len_m, energy_left_frac, depot_dist_m, fits):
    eps = 1e-12

    def clean(x, default, low=0.0):
        a = np.asarray(x, dtype=float)
        return np.maximum(np.nan_to_num(a, nan=default, posinf=default,
                                        neginf=low), low)

    d = clean(dist_m, 1e6)
    turn = np.mod(np.nan_to_num(np.asarray(turn_deg, dtype=float),
                                nan=180.0, posinf=180.0, neginf=180.0), 360.0)
    length = clean(swath_len_m, 1e6)
    depot = clean(depot_dist_m, 1e6)
    fit = np.clip(np.nan_to_num(np.asarray(fits, dtype=float),
                                nan=0.0, posinf=0.0, neginf=0.0), 0.0, 1.0)
    energy = float(np.clip(np.nan_to_num(energy_left_frac, nan=0.0,
                                         posinf=0.0, neginf=0.0), 0.0, 1.0))

    urgency = 1.0 - energy
    angle_error = np.abs((turn - 180.0 + 180.0) % 360.0 - 180.0)
    turn_factor = 1.0 + angle_error / 90.0

    work = d + length
    work_factor = 1.0 + work * (0.5 + 1.5 * urgency) / 100.0
    depot_factor = 1.0 + 2.0 * urgency * depot / (depot + 100.0)

    # Discourage barely feasible choices more as the current battery runs low.
    reserve_factor = 1.0 + 2.0 * urgency * work / (100.0 + work)
    feasibility_factor = 0.01 + 0.99 * fit

    score = feasibility_factor / ((1.0 + d) * turn_factor * work_factor *
                                  depot_factor * reserve_factor)
    return np.maximum(np.nan_to_num(score, nan=eps, posinf=1.0, neginf=eps), eps)
