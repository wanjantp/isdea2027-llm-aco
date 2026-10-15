import numpy as np

def heuristic(dist_m, turn_deg, swath_len_m, energy_left_frac, depot_dist_m, fits):
    """Strictly positive desirability scores for K candidate swaths (numpy arrays of length K)."""
    dist = np.asarray(dist_m, dtype=float)
    turn = np.asarray(turn_deg, dtype=float)
    length = np.asarray(swath_len_m, dtype=float)
    home = np.asarray(depot_dist_m, dtype=float)
    fit = np.asarray(fits, dtype=float)
    if dist.size == 0:
        return np.empty(0, dtype=float)
    eps = 1e-12
    frac = float(np.clip(energy_left_frac, 0.0, 1.0))
    drain = 1.0 - frac

    # Transit: smooth Gaussian reversal kernel (~180 deg passes are cheap), folded into overhead once.
    fold = np.minimum(turn, 360.0 - turn)
    reversal = np.exp(-0.5 * ((fold - 180.0) / 40.0) ** 2)
    turn_cost = 1.0 - 0.6 * reversal
    scale = dist.mean() + eps
    overhead = dist * (1.0 + 0.5 * turn_cost) + 10.0 * turn_cost * (dist / scale)
    transit = 1.0 / (1.0 + (overhead / 12.0) ** 2)

    # Productivity: useful length per unit overhead, batch-normalised into [0.4, 1].
    value = length / (overhead + eps)
    productivity = 0.4 + 0.6 * value / (value.max() + eps)

    # Depot/margin term (single pass): drain-gated closeness, with a margin penalty when spare energy goes negative.
    h_norm = home / (home.max() + eps)
    margin = np.clip(frac - h_norm * drain, -1.0, 1.0)
    closeness = np.exp(-3.0 * h_norm)
    pull = drain ** 2 * closeness
    depot = 1.0 - 0.4 * pull / (pull.max() + eps)
    depot *= np.where(margin < 0.0, 0.85, 1.0) + 0.15 * np.clip(margin, 0.0, 1.0)
    depot = np.maximum(depot, 0.55)

    # Feasibility: drain-scaled urgency penalty for non-fitting candidates, low floor keeps exploration alive.
    urgency = 0.3 + 0.7 * drain
    feas = np.maximum(1.0 - 0.85 * urgency * (1.0 - fit), 0.12)

    score = transit * productivity * depot * feas
    score = np.nan_to_num(score, nan=eps, posinf=1.0, neginf=eps)
    return np.maximum(score, eps)
