import numpy as np

def heuristic(dist_m, turn_deg, swath_len_m, energy_left_frac, depot_dist_m, fits):
    """Return a positive desirability score for each candidate swath (numpy arrays, same length).
    dist_m: distance to candidate start (m); turn_deg: turning needed (deg); swath_len_m: candidate length (m);
    energy_left_frac: battery fraction left (scalar 0..1); depot_dist_m: distance from candidate end to depot (m);
    fits: 1.0 if the candidate fits in the remaining battery, else 0.0."""
    turn_cost = np.log(1 + turn_deg / 180) ** 2.5 + (turn_deg / 180) ** 2  # Smoothly penalize sharp turns
    alignment_cost = np.minimum(1.0, turn_deg / 10)  # Penalize swaths that are not aligned with the current heading
    distance_cost = dist_m ** 1.7 + dist_m ** 3  # Heavily penalize large distances with a higher exponent
    fit_cost = 1.0 - fits  # Forced battery swaps are costly
    depot_proximity = (depot_dist_m + 1.0) ** -1.8  # Prefer swaths closer to the depot with a higher exponent
    energy_cost = (1.0 - energy_left_frac) ** 0.5  # Prefer swaths when energy is low
    next_turn_cost = dist_m / (swath_len_m + 1e-6)  # Penalize long stretches between turns
    adjacent_penalty = np.maximum(0, swath_len_m - 5)  # More aggressive penalty for adjacent parallel swaths
    swath_length_penalty = swath_len_m ** 0.5  # Penalize long swaths to encourage shorter turns and more frequent returns
    total_cost = distance_cost + turn_cost + alignment_cost + fit_cost + depot_proximity + energy_cost + next_turn_cost + adjacent_penalty + swath_length_penalty
    return 1.0 / total_cost  # Invert the total cost to get a heuristic score
