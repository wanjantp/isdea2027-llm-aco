import numpy as np

def heuristic(dist_m, turn_deg, swath_len_m, energy_left_frac, depot_dist_m, fits):
    base_score = 1.0 / (dist_m + 1.0)  # Base score based on distance
    turn_cost = 0.0 * turn_deg  # Reduced penalty for sharp turns
    turn_cost = turn_cost * 1.0  # Increased penalty for sharp turns when battery is low
    fit_bonus = fits * 55.0  # Balanced bonus for swaths that fit within battery
    depot_proximity = 1.0 / (depot_dist_m + 1.0)  # Bonus for swaths closer to depot
    energy_efficiency = swath_len_m / (swath_len_m * energy_left_frac)  # Higher energy efficiency is better
    battery_safety = 1.0 if energy_left_frac > 0.1 else 0.5  # Safety bonus for maintaining battery
    battery_savings_bonus = (energy_left_frac ** 2) * 10  # Additional bonus for preserving battery life
    dynamic_weight = (energy_left_frac * depot_dist_m) / (dist_m + 1)  # Adjust weight based on battery and distance
    path_length_penalty = dist_m + swath_len_m + depot_dist_m  # Penalize total path length
    next_dist_penalty = np.maximum(0, dist_m - 100) * 0.1  # Penalty for swaths ending far from the next candidate
    battery_fit_penalty = 1.0 / (fits + 1) if energy_left_frac < 0.1 else 1.0  # Reduced importance of battery fit when nearly depleted
    sharp_turn_penalty = 0.0 * turn_deg  # Penalize large turns
    next_swath_distance_bonus = 1.0 / (np.maximum(dist_m, 1.0))  # Bonus for swaths ending closer to the next candidate
    adjusted_score = base_score * (1.0 + fit_bonus + depot_proximity + energy_efficiency + battery_safety + battery_savings_bonus) / (1.0 + turn_cost + next_dist_penalty + sharp_turn_penalty) * dynamic_weight / (path_length_penalty + 1) * battery_fit_penalty * next_swath_distance_bonus
    adjusted_score *= (energy_left_frac ** 3)
    energy_efficiency_factor = (swath_len_m * energy_left_frac) / (swath_len_m + 1)
    adjusted_score *= energy_efficiency_factor
    return adjusted_score
