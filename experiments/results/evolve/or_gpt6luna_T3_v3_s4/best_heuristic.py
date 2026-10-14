import numpy as np

def heuristic(dist_m, turn_deg, swath_len_m, energy_left_frac, depot_dist_m, fits):
    def clean(x, default, high=1e12):
        return np.nan_to_num(
            np.asarray(x, dtype=float), nan=default,
            posinf=high, neginf=default
        )

    dist = np.maximum(clean(dist_m, 1e12), 0.0)
    turn = clean(turn_deg, 180.0)
    length = np.maximum(clean(swath_len_m, 1e12), 0.0)
    depot = np.maximum(clean(depot_dist_m, 1e12), 0.0)
    fit = clean(fits, 0.0)
    remaining = float(np.clip(clean(energy_left_frac, 0.0), 0.0, 1.0))

    turn_error = np.abs((turn - 180.0 + 180.0) % 360.0 - 180.0)
    turn_quality = 1.0 / (1.0 + (turn_error / 52.0) ** 2)
    proximity = 1.0 / (1.0 + dist / 250.0)
    turn_factor = 0.72 + 0.28 * proximity * turn_quality

    pressure = 1.0 - remaining
    depot_weight = 0.20 + 0.90 * pressure**2
    depot_factor = 1.0 / (1.0 + depot_weight * depot / 900.0)
    length_factor = 1.0 / (1.0 + length / 1400.0)

    burden = dist + length + depot
    reserve_scale = 1.0 + 1800.0 * remaining
    reserve_risk = np.maximum(burden / reserve_scale - 0.65, 0.0)
    reserve_factor = 1.0 / (1.0 + reserve_risk**2)

    fit_factor = np.where(fit >= 0.5, 1.0, 0.08 + 0.12 * remaining)
    score = turn_factor * depot_factor * length_factor * reserve_factor
    score *= fit_factor / (1.0 + dist)

    return np.maximum(
        np.nan_to_num(score, nan=1e-12, posinf=1e12, neginf=1e-12),
        1e-12
    )
