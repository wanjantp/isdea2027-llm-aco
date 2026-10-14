import numpy as np

def heuristic(dist_m, turn_deg, swath_len_m, energy_left_frac, depot_dist_m, fits):
    eps = 1e-12

    def clean(x, default):
        return np.nan_to_num(np.asarray(x, dtype=float), nan=default,
                             posinf=default, neginf=default)

    dist = np.maximum(clean(dist_m, 1e6), 0.0)
    turn = np.clip(clean(turn_deg, 360.0), 0.0, 360.0)
    length = np.maximum(clean(swath_len_m, 1e6), 0.0)
    depot = np.maximum(clean(depot_dist_m, 1e6), 0.0)
    fit = clean(fits, 0.0)
    battery = float(np.clip(np.nan_to_num(energy_left_frac, nan=0.0,
                                           posinf=1.0, neginf=0.0), 0.0, 1.0))

    length_scale = max(float(np.median(length)), eps)
    depot_scale = max(float(np.median(depot)), eps)

    travel_pref = 1.0 / (1.0 + dist)
    # Blend a gentle-turn preference with a modest preference for U-turns
    # that commonly occur between adjacent parallel swaths.
    turn_pref = (1.0 / (1.0 + turn / 90.0)) * (
        1.0 + 0.25 * np.exp(-0.5 * ((turn - 180.0) / 35.0) ** 2)
    )
    length_pref = 1.0 / (1.0 + 0.35 * length / length_scale)
    depot_pref = 1.0 / (1.0 + depot / depot_scale)

    # Make depot proximity matter more as the current sortie approaches depletion.
    urgency = (1.0 - battery) ** 2
    return_pref = np.exp(-1.5 * urgency * (1.0 - depot_pref))
    fit_pref = np.where(fit >= 0.5, 1.0, 0.005)

    score = travel_pref * turn_pref * length_pref * return_pref * fit_pref
    return np.maximum(np.nan_to_num(score, nan=eps, posinf=1.0, neginf=eps), eps)
