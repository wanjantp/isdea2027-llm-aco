import numpy as np

def heuristic(dist_m, turn_deg, swath_len_m, energy_left_frac, depot_dist_m, fits):
    # Normalize turn angle cyclically around 180° (straight continuation)
    turn_norm = np.mod(turn_deg, 360.0)
    angular_score = (np.cos(np.radians(turn_norm - 180.0)) + 1.0) / 2.0

    # Geometric continuity: inverse distance weighted by swath length
    dist_safe = np.maximum(dist_m, 1e-6)
    dist_score = 1.0 / dist_safe
    geo_bonus = 1.0 / (1.0 + dist_safe / swath_len_m)
    base_geo_score = dist_score * (0.95 + 0.05 * angular_score) * geo_bonus

    # Dynamic energy strategy: If battery is critical (<10%), prioritize returning to depot regardless of geometry
    # Otherwise, use the previous feasibility gate scaled by remaining capacity
    energy_threshold = 0.1
    if energy_left_frac < energy_threshold:
        return base_geo_score * (fits + (1.0 - fits) * (depot_dist_m / 2500.0))
    
    # Standard mode: Penalize infeasible moves based on return distance and remaining buffer
    return np.maximum(base_geo_score * (fits + (1.0 - fits) * (depot_dist_m / 3000.0)), 1e-6)
