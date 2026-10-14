import numpy as np

def heuristic(dist_m, turn_deg, swath_len_m, energy_left_frac,
              depot_dist_m, fits):
    eps = np.finfo(float).tiny

    def clean(x, nan=0.0, pos=1e12):
        return np.nan_to_num(np.asarray(x, dtype=float), nan=nan,
                             posinf=pos, neginf=0.0)

    dist = np.maximum(clean(dist_m, nan=1e12), 0.0)
    turn = np.clip(clean(turn_deg, nan=180.0, pos=360.0), 0.0, 360.0)
    length = np.maximum(clean(swath_len_m), 0.0)
    depot = np.maximum(clean(depot_dist_m, nan=1e12), 0.0)
    fit = np.clip(clean(fits), 0.0, 1.0)
    battery = float(np.clip(np.nan_to_num(
        energy_left_frac, nan=0.0, posinf=1.0, neginf=0.0), 0.0, 1.0))
    scarcity = 1.0 - battery

    demand_raw = dist + 0.5 * length + depot
    demand = demand_raw / (demand_raw + 500.0)

    move_cost = (1.0 + 1.6 * scarcity) * (
        np.log1p(dist) + 0.22 * np.log1p(length))
    move_cost += 0.68 * turn / 180.0
    move_cost += 0.32 * scarcity * dist / (dist + 250.0)
    score = np.exp(-np.minimum(move_cost, 700.0))

    risk = scarcity * (0.4 + 0.6 * demand)
    score *= np.exp(-(1.0 - fit) * (2.0 + 4.0 * risk))

    depot_pressure = scarcity * (0.3 + 0.7 * demand)
    depot_scale = 300.0 + 900.0 * battery
    score *= np.exp(-1.7 * depot_pressure * depot / (depot + depot_scale))

    return np.maximum(np.nan_to_num(score, nan=eps, posinf=1.0,
                                    neginf=eps), eps)
