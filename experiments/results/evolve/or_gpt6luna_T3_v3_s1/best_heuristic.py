import numpy as np

def heuristic(dist_m, turn_deg, swath_len_m, energy_left_frac, depot_dist_m, fits):
    tiny = np.finfo(float).tiny

    def nonnegative(x):
        x = np.asarray(x, dtype=float)
        return np.maximum(np.nan_to_num(x, nan=0.0, posinf=1e12, neginf=0.0), 0.0)

    dist = nonnegative(dist_m)
    length = nonnegative(swath_len_m)
    depot = nonnegative(depot_dist_m)
    turn = np.clip(np.nan_to_num(np.asarray(turn_deg, dtype=float),
                                 nan=180.0, posinf=360.0, neginf=0.0), 0.0, 360.0)
    feasible = np.clip(np.nan_to_num(np.asarray(fits, dtype=float),
                                     nan=0.0, posinf=0.0, neginf=0.0), 0.0, 1.0)
    battery = float(np.clip(np.nan_to_num(energy_left_frac, nan=0.0,
                                          posinf=1.0, neginf=0.0), 0.0, 1.0))

    scarcity = (1.0 - battery) / (battery + 0.08)
    urgency = scarcity**2 / (1.0 + scarcity**2)
    depot_burden = depot / (depot + 100.0)
    demand_scale = (dist + length + depot) / (dist + length + depot + 100.0)

    travel_cost = np.log1p(dist) + 0.35 * np.sqrt(dist)
    turn_cost = 0.8 * turn / 90.0
    return_cost = (0.25 + 2.5 * urgency) * depot_burden
    reserve_cost = 1.5 * urgency * demand_scale
    infeasible_cost = (1.0 - feasible) * (
        6.0 + 4.0 * urgency + 3.0 * urgency * depot_burden
    )

    log_cost = travel_cost + turn_cost + return_cost + reserve_cost + infeasible_cost
    score = np.exp(-np.minimum(log_cost, 700.0))
    return np.maximum(np.nan_to_num(score, nan=tiny, posinf=1.0, neginf=tiny), tiny)
