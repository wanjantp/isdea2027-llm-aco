import numpy as np

def heuristic(dist_m, turn_deg, swath_len_m, energy_left_frac, depot_dist_m, fits):
    """Combine short-hop preference, ideal 180° turns, and critical battery proximity."""
    # Normalize turn deviation: 0 for perfect 180°, larger for other angles
    turn_norm = np.abs(turn_deg - 180.0) / 90.0
    
    # Utility score: swath length weighted by feasibility (fits), plus constant to avoid zeros
    utility_score = swath_len_m * fits + 1.0
    
    # Inverse transit distance with strong penalty for large values
    dist_inv = 1.0 / (dist_m + 1e-6)
    
    # Composite base score: high when distance is small and utility is high
    # Denominator balances raw distance and turn cost to avoid selecting long hops
    base_score = dist_inv * (utility_score + 1.0) / (dist_m + turn_norm * 2.0 + 1e-3)
    
    # Battery-aware adjustment: when battery is critically low, heavily boost swaths near depot
    low_battery_threshold = 0.25
    energy_factor = 1.0
    if energy_left_frac < low_battery_threshold:
        deficit_ratio = (low_battery_threshold - energy_left_frac) / (low_battery_threshold + 1e-6)
        # Exponentiate distance penalty to make far depot entries very unlikely when low on battery
        energy_factor = 1.0 - deficit_ratio * np.minimum(1.0, depot_dist_m / 100.0)
    
    return np.maximum(base_score * energy_factor, 1e-6)
