import numpy as np

def heuristic(dist_m, turn_deg, swath_len_m, energy_left_frac, depot_dist_m, fits):
    feasibility_gate = np.where(fits == 1.0, 1.0, 1e-9)
    dist_factor = 1.0 / np.maximum(dist_m, 1.0) ** 4.5
    turn_rad = np.radians(np.minimum(np.abs(turn_deg % 360), 180.0))
    turn_score = 3.0 * (1.0 - (turn_rad - np.pi) / np.pi) + 1.0
    transit_energy = dist_m + swath_len_m + depot_dist_m
    battery_range = np.clip(energy_left_frac * 600.0, 0.1, float('inf'))
    dynamic_battery_factor = np.clip((battery_range - transit_energy) / (transit_energy + 1.0), -2.0, 1.0)
    safety_factor = (depot_dist_m + 1.0) / (depot_dist_m + 30.0) * (0.5 + (1.0 - energy_left_frac) * 2.0)
    swath_efficiency = np.clip(1.0 + 0.3 * (swath_len_m / 600.0) * (1.0 + dynamic_battery_factor), 0.8, 2.0)
    return dist_factor * turn_score * swath_efficiency * feasibility_gate * safety_factor
