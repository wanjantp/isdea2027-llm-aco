import numpy as np

def heuristic(dist_m, turn_deg, swath_len_m, energy_left_frac, depot_dist_m, fits):
    theta = np.radians(turn_deg)
    angle_score = 1.0 / (1.0 + 0.2 * np.abs(theta - np.pi))
    
    dist_score = 1.0 / ((dist_m / 50.0) ** 2 + 1e-4)
    
    length_reward = swath_len_m / (swath_len_m + 1e-6)
    
    urgency_factor = 1.0 + (1.0 - energy_left_frac) ** 1.5
    relative_return = depot_dist_m / (swath_len_m + 1e-6) * np.clip(urgency_factor, 1.0, 4.0)
    
    combined_geom = angle_score * dist_score * length_reward * (1.0 + relative_return)
    
    fit_modifier = 0.5 + 0.5 * fits
    
    return combined_geom * fit_modifier
