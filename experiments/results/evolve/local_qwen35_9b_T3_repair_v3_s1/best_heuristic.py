import numpy as np

def heuristic(dist_m, turn_deg, swath_len_m, energy_left_frac, depot_dist_m, fits):
    eps = 1e-4
    # Dynamic risk scaling: when battery is low (fits=0), incorporate future transit cost; otherwise standard proximity
    risk_multiplier = np.where(fits == 0.0, 1.0 / (energy_left_frac + eps), 1.0)
    
    # Proximity attraction penalized by the dynamic risk multiplier to avoid high-cost jumps when battery is low
    base_attraction = (1.0 / (dist_m + eps) ** 2) / risk_multiplier
    
    # Turn preference: strictly favor 180 degrees but allow slight deviation if it brings the end point closer to depot
    ideal_turn = np.where(depot_dist_m < 500.0, 0.0, 180.0)
    turn_deviation = np.abs(np.mod(turn_deg, 360.0) - ideal_turn)
    turn_factor = np.exp(-1.0 * turn_deviation / 90.0)
    
    # Energy risk combines path length with a super-linear penalty as battery depletes, gated by feasibility
    energy_path = swath_len_m + dist_m
    energy_risk = (energy_path + eps) / ((energy_left_frac + eps) ** 2.2) * np.where(fits == 0.0, 1.0, 0.5)
    
    return base_attraction * turn_factor / (1.0 + energy_risk)
