import numpy as np

def heuristic(dist_m, turn_deg, swath_len_m, energy_left_frac, depot_dist_m, fits):
    """Strictly positive desirability (higher = better) for K candidate (swath, direction) moves."""
    eps = 1e-9
    frac = float(np.clip(energy_left_frac, 0.0, 1.0))
    dist = np.nan_to_num(np.asarray(dist_m, dtype=float), nan=1e6, posinf=1e6)
    length = np.nan_to_num(np.asarray(swath_len_m, dtype=float), nan=0.0, posinf=1e6)
    depot = np.nan_to_num(np.asarray(depot_dist_m, dtype=float), nan=1e6, posinf=1e6)
    turn = np.nan_to_num(np.asarray(turn_deg, dtype=float), nan=0.0) % 360.0
    fits_arr = np.clip(np.nan_to_num(np.asarray(fits, dtype=float), nan=0.0), 0.0, 1.0)

    # Turn-adjusted approach (bounded separation in [0,1]) and scale-normalised transit term
    sep = np.minimum(turn, 360.0 - turn) / 180.0
    approach = np.maximum(dist * (1.0 + 0.5 * sep), eps)
    scale = approach.mean() + eps
    sens = 1.0 + 2.0 * (1.0 - frac)
    log_transit = -sens * approach / scale - np.log(approach)

    # Bounded productivity and turn factors in log domain
    leg = approach + length + eps
    log_prod = np.log(0.5 + 0.5 * length / leg)
    log_turn = np.log(0.5 + 0.5 * sep)

    # Single shared dimensionless battery margin drives urgency and feasibility
    budget = np.maximum(frac * leg, eps)
    margin = (budget - depot) / budget
    tight = np.logaddexp(0.0, -8.0 * margin) / np.log(2.0)
    log_urg = np.log1p((1.0 - frac) ** 2 * tight)          # in [0, log 2]

    # Feasibility: hard fit blended with soft near-fit, floor-bounded so nothing is zeroed
    near = 1.0 / (1.0 + np.exp(-6.0 * (margin + 0.1)))
    feas = 0.3 + 0.7 * np.maximum(fits_arr, 0.5 * near)
    log_feas = np.log(feas)

    # Shift by max in log domain before exponentiating
    log_score = log_transit + log_prod + log_turn + log_urg + log_feas
    log_score = np.where(np.isfinite(log_score), log_score, np.log(eps))
    shifted = np.exp(log_score - log_score.max())
    return np.clip(shifted + eps, eps, 1e6)
