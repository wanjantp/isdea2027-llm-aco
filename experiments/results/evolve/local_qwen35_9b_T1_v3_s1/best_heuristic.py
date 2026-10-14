import numpy as np

def heuristic(dist_m, turn_deg, swath_len_m, energy_left_frac, depot_dist_m, fits):
    eps = 1e-6
    # Estimate total cost for this candidate: transit + swath + minimal turnaround overhead
    estimated_cost = dist_m + swath_len_m + 1.0
    
    # Energy ratio term: penalizes high cost relative to remaining battery capacity
    # If energy_left_frac is low, this term drops significantly, discouraging risky moves
    safe_energy = np.maximum(energy_left_frac, eps)
    energy_term = (safe_energy + estimated_cost * 0.01) / (safe_energy + estimated_cost * 0.05)
    
    # Distance decay: strongly favors closer candidates
    dist_term = np.exp(-0.3 * dist_m)
    
    # Turn penalty: favors smaller turn angles (closer to straight line or previous direction)
    turn_term = np.exp(-0.5 * np.abs(turn_deg))
    
    return dist_term * energy_term * turn_term
