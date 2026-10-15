import numpy as np

def heuristic(dist_m, turn_deg, swath_len_m, energy_left_frac, depot_dist_m, fits):
    """Strictly positive, finite, bounded desirability per candidate swath (higher = better)."""
    eps = 1e-9
    dist = np.asarray(dist_m, dtype=float)
    turn = np.asarray(turn_deg, dtype=float)
    length = np.asarray(swath_len_m, dtype=float)
    back = np.asarray(depot_dist_m, dtype=float)
    fit = np.asarray(fits, dtype=float)
    e = float(np.clip(energy_left_frac, 0.0, 1.0))
    d = 1.0 - e  # depletion: 0 full, 1 empty

    # Transit: inverse distance, sharpened by depletion (bounded since dist+1 >= 1).
    transit = 1.0 / (dist + 1.0) ** (1.0 + d)

    # Turn: depletion-sharpened quadratic penalty plus a bounded ~180 deg reversal bonus.
    turn_frac = turn / 180.0
    turn_mod = (1.0 / (1.0 + 0.5 * turn_frac ** 2)) ** (1.0 + d)
    reversal = 1.0 + 0.15 * np.exp(-((turn - 180.0) / 45.0) ** 2)

    # Productivity: flown share of the leg, turn overhead as equivalent length, in [0.5, 1].
    share = length / (dist + 0.5 * turn_frac * length + length + eps)
    productivity = 0.5 + 0.5 * share

    # Scale-free energy margin: fraction of the candidate's own leg requirement, gated by d.
    need = dist + length + back
    margin = 1.0 - 0.4 * d * need / (need + e * np.max(need) + eps)
    margin = np.clip(margin, 0.6, 1.0)

    # Depot-return bias gated by d^2 (neutral when full), bounded in [0.75, 1].
    return_share = back / (back + length + eps)
    depot_mod = 1.0 - 0.25 * d ** 2 * return_share

    # Soft feasibility that never vetoes: strength grows with depletion.
    feas_strength = 0.35 + 0.30 * d
    feas_mod = np.clip((1.0 - feas_strength) + feas_strength * fit, 0.2, 1.0)

    score = (transit * turn_mod * reversal * productivity
             * margin * depot_mod * feas_mod)
    return np.clip(score, eps, 1e3) * np.ones_like(dist)
