import numpy as np

def heuristic(dist_m, turn_deg, swath_len_m, energy_left_frac, depot_dist_m, fits):
    # Normalize distances by field scale (swath length) to make metric invariant
    dist_norm = dist_m / (swath_len_m + 1.0)
    # Normalize turn angle by pi to treat reversals as significant penalties
    turn_norm = np.radians(turn_deg) / np.pi
    
    # Combine normalized geometric costs multiplicatively to penalize joint high-distance/turn events
    geo_score = np.exp(-0.3 * (dist_norm + turn_norm))
    
    # Energy constraint: score decays strictly as battery drops below 20%, vanishing near 0%
    energy_penalty = np.exp(-20.0 * np.maximum(energy_left_frac - 0.2, 0.0))
    
    # Final score is product of geometric desirability and energy safety, ensuring strict positivity
    return geo_score * energy_penalty
