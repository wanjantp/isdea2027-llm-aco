import numpy as np

def heuristic(dist_m, turn_deg, swath_len_m, energy_left_frac, depot_dist_m, fits):
    """Return a positive desirability score for each candidate swath (numpy arrays, same length).
    dist_m: distance to candidate start (m); turn_deg: turning needed (deg); swath_len_m: candidate length (m);
    energy_left_frac: battery fraction left (scalar 0..1); depot_dist_m: distance from candidate end to depot (m);
    fits: 1.0 if the candidate fits in the remaining battery, else 0.0."""
    turn_cost = (turn_deg / 360) ** 2.4 * 125  # Balanced turn penalty
    battery_cost = (1 - fits) * 1400 / (1 + energy_left_frac) ** 1.07
    depot_bonus = (depot_dist_m / dist_m) ** 3.25 * 200  # High exponent for depot bonus
    distance_cost = (dist_m / 100) ** 1.60 * 1.15  # Intermediate distance cost exponent
    score = (1 / (swath_len_m + 1)) / (turn_cost + battery_cost + distance_cost) * depot_bonus
    return score * (energy_left_frac ** 0.42)  # Moderately adjusted battery fraction scaling
