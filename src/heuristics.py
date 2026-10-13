"""Heuristic functions eta(state) for ACO. This is the ONLY component that differs between methods.

Signature every heuristic must follow (vectorised over the K candidate (swath, direction) nodes):

    def heuristic(dist_m, turn_deg, swath_len_m, energy_left_frac, depot_dist_m, fits) -> np.ndarray[K] > 0

    dist_m           distance from current position to the candidate's start point (m)
    turn_deg         total turning angle needed to leave current heading and align with the candidate (deg, 0..360)
    swath_len_m      length of the candidate swath (m)
    energy_left_frac fraction of usable battery left in the current sortie (scalar, 0..1)
    depot_dist_m     distance from the candidate's END point back to the depot (m)
    fits             1.0 if (go + fly + return) fits the remaining energy, else 0.0

Returns desirability per candidate (higher = better). Must be finite and > 0.
LLM-evolved heuristics implement exactly this function (see TEMPLATE_* strings below).
"""
from __future__ import annotations
import numpy as np

EPS = 1e-6


# ---- B2: distance only (standard ACO) ----------------------------------------------------
def h_distance(dist_m, turn_deg, swath_len_m, energy_left_frac, depot_dist_m, fits):
    return 1.0 / (dist_m + 1.0)


# ---- B3: human-designed, MS-ACO style: distance + corner (turn) cost ----------------------
# LOCKED 2026-10-13 after grid search on the validation split (experiments/tune_baselines.py, 25 fields x 3 seeds):
#   w_turn in {0,0.05,0.1,0.25,0.5,1.0}: ratio-to-B1 0.9662, 0.9671, 0.9688, 0.9723, 0.9788, 0.9900 -> optimum is 0 (= B2).
#   We keep the best NON-ZERO weight (0.05) so B3 remains a genuine turn-aware hand-crafted heuristic; report the trend in the paper.
def h_dist_turn(dist_m, turn_deg, swath_len_m, energy_left_frac, depot_dist_m, fits, w_turn=0.05):
    # turn cost expressed in equivalent metres per degree
    return 1.0 / (dist_m + w_turn * turn_deg + 1.0)


# ---- B4: human-designed, battery-aware (our fair hand-crafted competitor) ------------------
# LOCKED 2026-10-13: grid over w_turn x w_depot ({0..1} x {0..2}) -> optimum w_turn=0, w_depot=0 (0.9669, i.e. no better than B2).
#   Best non-zero pair kept: w_turn=0.05, w_depot=0.25 (0.9678).
def h_dist_turn_battery(dist_m, turn_deg, swath_len_m, energy_left_frac, depot_dist_m, fits, w_turn=0.05, w_depot=0.25):
    base = 1.0 / (dist_m + w_turn * turn_deg + 1.0)
    # when the battery is low, prefer swaths that end close to the depot; infeasible ones are strongly discouraged
    low = np.clip(1.0 - energy_left_frac, 0, 1)
    depot_pref = 1.0 / (1.0 + w_depot * low * depot_dist_m / 100.0)
    return base * depot_pref * np.where(fits > 0.5, 1.0, 0.05)


BASELINES = {
    "B2_distance": h_distance,
    "B3_dist_turn": h_dist_turn,
    "B4_dist_turn_battery": h_dist_turn_battery,
}


# ---- Templates handed to the LLM (ablation T1 / T2 / T3) ----------------------------------
TEMPLATE_T3_FULL = '''
import numpy as np

def heuristic(dist_m, turn_deg, swath_len_m, energy_left_frac, depot_dist_m, fits):
    """Return a positive desirability score for each candidate swath (numpy arrays, same length).
    dist_m: distance to candidate start (m); turn_deg: turning needed (deg); swath_len_m: candidate length (m);
    energy_left_frac: battery fraction left (scalar 0..1); depot_dist_m: distance from candidate end to depot (m);
    fits: 1.0 if the candidate fits in the remaining battery, else 0.0."""
    return 1.0 / (dist_m + 1.0)
'''

TEMPLATE_T2_GEOM = '''
import numpy as np

def heuristic(dist_m, turn_deg, swath_len_m, energy_left_frac, depot_dist_m, fits):
    """Return a positive desirability score per candidate. Only dist_m, turn_deg and swath_len_m carry information;
    the remaining arguments are provided for interface compatibility and are constant."""
    return 1.0 / (dist_m + 1.0)
'''

TEMPLATE_T1_DIST = '''
import numpy as np

def heuristic(dist_m, turn_deg, swath_len_m, energy_left_frac, depot_dist_m, fits):
    """Return a positive desirability score per candidate. Only dist_m carries information;
    the remaining arguments are provided for interface compatibility and are constant."""
    return 1.0 / (dist_m + 1.0)
'''


def mask_for_template(template: str):
    """Returns a function that blanks out features not visible in the given template (for ablation)."""
    if template == "T1":
        return lambda d, t, l, e, dd, f: (d, np.zeros_like(t), np.zeros_like(l), 1.0, np.zeros_like(dd), np.ones_like(f))
    if template == "T2":
        return lambda d, t, l, e, dd, f: (d, t, l, 1.0, np.zeros_like(dd), np.ones_like(f))
    return lambda d, t, l, e, dd, f: (d, t, l, e, dd, f)


def load_heuristic_from_code(code: str, timeout_s: float = 2.0):
    """Compile LLM-generated code into a callable; validates on a random input. Raises on failure."""
    import math, signal
    ns = {}
    exec(compile(code, "<llm_heuristic>", "exec"), {"np": np, "numpy": np, "math": math, "__builtins__": __builtins__}, ns)
    fn = ns.get("heuristic")
    if fn is None:
        raise ValueError("no function named 'heuristic'")
    rng = np.random.default_rng(0)
    K = 16
    out = fn(rng.uniform(0, 500, K), rng.uniform(0, 360, K), rng.uniform(5, 400, K), 0.5, rng.uniform(0, 600, K), rng.integers(0, 2, K).astype(float))
    out = np.asarray(out, dtype=float)
    if out.shape != (K,) or not np.all(np.isfinite(out)) or np.any(out <= 0):
        raise ValueError(f"invalid output: shape={out.shape}, finite={np.all(np.isfinite(out))}, min={out.min() if out.size else None}")
    return fn
