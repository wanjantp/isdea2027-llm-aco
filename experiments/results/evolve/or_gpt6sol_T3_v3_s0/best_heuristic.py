import numpy as np

def heuristic(dist_m, turn_deg, swath_len_m, energy_left_frac,
              depot_dist_m, fits):
    def clean(x, upper):
        x = np.asarray(x, dtype=float)
        return np.clip(np.nan_to_num(x, nan=0.0, posinf=upper,
                                     neginf=0.0), 0.0, upper)

    d = clean(dist_m, 1e9)
    if d.size == 0:
        return np.empty(0, dtype=float)

    turn = clean(turn_deg, 360.0)
    length = clean(swath_len_m, 1e9)
    depot = clean(depot_dist_m, 1e9)
    fit = clean(fits, 1.0) >= 0.5
    battery = float(clean(energy_left_frac, 1.0))

    approach = d + 2.5 * turn / 180.0
    reference = np.min(approach[fit]) if np.any(fit) else np.min(approach)

    # Compare extra approach cost with the work gained, rather than
    # scaling the distance penalty by swath length alone.
    extra = np.maximum(approach - reference, 0.0)
    productive = length / (length + 100.0)
    transit = 1.0 / (1.0 + extra / (1.0 + 1.8 * productive))

    efficiency = (1.0 + d / (length + 60.0)) ** -0.20
    coverage = 1.0 + 0.10 * productive
    turning = 1.0 / (1.0 + 0.32 * turn / 180.0)

    pressure = np.clip((0.62 - battery) / 0.62, 0.0, 1.0) ** 2
    homeward = 1.0 - 0.28 * pressure * depot / (depot + length + 100.0)

    saving = np.maximum(reference - approach, 0.0)
    swap_penalty = 0.77 + 0.18 * saving / (saving + 40.0)
    if not np.any(fit):
        swap_penalty = np.full_like(d, 0.95)

    score = transit * efficiency * coverage * turning
    score *= np.where(fit, homeward, swap_penalty)
    return np.maximum(np.nan_to_num(score, nan=0.0, posinf=0.0,
                                    neginf=0.0), np.finfo(float).tiny)
