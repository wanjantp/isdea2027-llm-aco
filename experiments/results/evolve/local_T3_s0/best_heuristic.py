import numpy as np

def heuristic(dist_m, turn_deg, swath_len_m, energy_left_frac, depot_dist_m, fits):
    base_score = dist_m**-2 * np.exp(-turn_deg / 80)  # Adjusted exponential decay for sharp turns
    fit_bonus = np.where(fits > 0.95, 4.5, 1.6)
    next_swath_proximity = np.maximum(0.3, 1 - (dist_m / 250))  # Enhanced proximity to depot with adjusted floor and ceiling
    energy_usage_penalty = (energy_left_frac + 0.1) ** (-4.0)  # Slightly more aggressive penalty for battery usage
    parallel_balance = np.where(np.abs(turn_deg) < 20, 4.5, 0.7)  # Enhanced balance for nearly parallel swaths
    dynamic_turn_cost = 1 + (energy_left_frac * depot_dist_m / 800) * turn_deg**0.6  # More aggressive adaptive turn penalty
    return base_score * fit_bonus * next_swath_proximity * energy_usage_penalty * parallel_balance * dynamic_turn_cost
