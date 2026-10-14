import numpy as np

def heuristic(dist_m, turn_deg, swath_len_m, energy_left_frac, depot_dist_m, fits):
    def clean(x, nan=0.0):
        a = np.asarray(x, dtype=float)
        return np.maximum(np.nan_to_num(a, nan=nan, posinf=1e12, neginf=0.0), 0.0)

    dist = clean(dist_m, 1e6)
    turn = np.mod(clean(turn_deg), 360.0) / 180.0
    length = clean(swath_len_m)
    depot = clean(depot_dist_m, 1e6)
    feasible = np.clip(clean(fits), 0.0, 1.0)
    energy = float(np.clip(np.nan_to_num(
        energy_left_frac, nan=0.0, posinf=1.0, neginf=0.0
    ), 0.0, 1.0))

    travel = dist + 0.08 * length
    turn_cost = 0.30 * turn + 0.45 * turn**2
    cost = travel * (1.0 + turn_cost)
    cost += 0.15 * turn**2
    cost += 0.08 * length / (1.0 + 0.08 * length)

    urgency = (1.0 - energy)**2
    depot_scale = depot / (1.0 + depot)
    swap_penalty = (1.0 - feasible) * (
        0.7 + 3.5 * energy + 1.2 * urgency * depot_scale
    )

    log_score = -np.minimum(cost, 700.0) / 10.0 - np.log1p(swap_penalty)
    score = np.exp(np.maximum(log_score, -700.0))
    return np.maximum(np.nan_to_num(
        score, nan=1e-12, posinf=1.0, neginf=1e-12
    ), 1e-12)
