"""UAV energy / time model and route evaluation with battery sorties.

Model (stated in the paper; keep identical for all methods):
    E_total = sum_i P_work * d_i / v_work            (working swaths)
            + sum_k [P_transit * d_k / v_transit]     (connections between swaths, depot legs)
            + sum_turns [P_hover * theta/omega + c_turn * theta/180]
            + n_sorties * E_swap (fixed overhead: take-off, landing, battery swap)
Battery: a sortie must finish at the depot with remaining energy >= reserve.
The sortie split is decided greedily during route evaluation (same policy for every method), so the
only thing a planner controls is the ORDER and DIRECTION of swaths.

Default parameters are placeholders for a mid-size agricultural spray drone. TODO before paper:
calibrate P_* from Rodrigues et al. (2022, Patterns) coefficients scaled to the chosen airframe,
and cite the airframe spec sheet. Put the final values in data/energy/uav_params.json.
"""
from __future__ import annotations
import math, json
from dataclasses import dataclass, asdict
from typing import Sequence
from swaths import Swath


@dataclass
class UAVModel:
    name: str = "placeholder_spray_drone"
    v_work: float = 5.0          # m/s along swaths
    v_transit: float = 10.0      # m/s between swaths / to depot
    P_work: float = 3500.0       # W while working (spraying / sensing)
    P_transit: float = 3000.0    # W in transit
    P_hover: float = 3200.0      # W while turning (near hover)
    omega: float = 90.0          # deg/s yaw rate in turns
    c_turn: float = 1500.0       # J extra per 180-degree turn (decel + accel)
    E_battery: float = 2.8e6     # J usable per sortie (~780 Wh)
    reserve_frac: float = 0.15   # keep 15 % reserve
    E_swap: float = 60_000.0     # J overhead per sortie (take-off, landing)
    t_swap: float = 180.0        # s overhead per sortie (landing + swap + take-off)

    @property
    def E_usable(self) -> float:
        return self.E_battery * (1 - self.reserve_frac)

    def save(self, path): json.dump(asdict(self), open(path, "w"), indent=1)
    @classmethod
    def load(cls, path): return cls(**json.load(open(path)))


def dist(a, b) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def heading(a, b) -> float:
    return math.atan2(b[1] - a[1], b[0] - a[0])


def turn_angle_deg(h_in: float, h_out: float) -> float:
    d = abs((h_out - h_in + math.pi) % (2 * math.pi) - math.pi)
    return math.degrees(d)


class Costs:
    """Pre-computed costs between swath endpoints for a given field. Index: swath i, direction d (0: p0->p1, 1: p1->p0).

    start(i,d), end(i,d): endpoint coords
    work_E[i], work_T[i]: energy/time to fly swath i
    transit(a, b): energy, time for straight flight between two points
    turn(h_in, h_out): energy, time of a turn
    """
    def __init__(self, swaths: Sequence[Swath], depot: tuple[float, float], m: UAVModel):
        self.sw, self.depot, self.m = swaths, depot, m
        self.n = len(swaths)
        self.work_E = [m.P_work * s.length / m.v_work for s in swaths]
        self.work_T = [s.length / m.v_work for s in swaths]
        self.ends = [(s.p0, s.p1) for s in swaths]

    def start(self, i, d): return self.ends[i][d]
    def end(self, i, d): return self.ends[i][1 - d]
    def head(self, i, d):
        a, b = self.start(i, d), self.end(i, d)
        return heading(a, b)

    def transit(self, a, b):
        d = dist(a, b)
        return self.m.P_transit * d / self.m.v_transit, d / self.m.v_transit

    def turn(self, h_in, h_out):
        th = turn_angle_deg(h_in, h_out)
        t = th / self.m.omega
        return self.m.P_hover * t + self.m.c_turn * th / 180.0, t, th

    def leg_cost(self, i, di, j, dj):
        """Energy, time, turn angle to go from end of (i,di) to start of (j,dj) and align with it."""
        e1, t1 = self.transit(self.end(i, di), self.start(j, dj))
        # two turns: leave swath i towards j, then align onto j
        h_leave = heading(self.end(i, di), self.start(j, dj)) if dist(self.end(i, di), self.start(j, dj)) > 1e-6 else self.head(j, dj)
        e2, t2, th2 = self.turn(self.head(i, di), h_leave)
        e3, t3, th3 = self.turn(h_leave, self.head(j, dj))
        return e1 + e2 + e3, t1 + t2 + t3, th2 + th3

    def depot_to(self, j, dj):
        e, t = self.transit(self.depot, self.start(j, dj))
        return e, t

    def to_depot(self, i, di):
        e, t = self.transit(self.end(i, di), self.depot)
        return e, t


@dataclass
class RouteResult:
    energy_J: float
    time_s: float
    n_sorties: int
    dist_work_m: float
    dist_transit_m: float
    total_turn_deg: float
    sorties: list                 # list of lists of (swath_idx, dir)
    feasible: bool


def evaluate_route(order: Sequence[tuple[int, int]], C: Costs) -> RouteResult:
    """Greedy sortie split: fly swaths in the given order; before each swath check that
    (go there + fly it + return to depot) fits the remaining usable energy, else return and start a new sortie."""
    m = C.m
    E = T = 0.0
    dist_work = dist_transit = turns = 0.0
    sorties, cur = [], []
    rem = C.m.E_usable
    E += m.E_swap; T += m.t_swap
    prev = None   # (i, d)
    feasible = True
    for (j, dj) in order:
        if prev is None:
            e_go, t_go = C.depot_to(j, dj); th = 0.0
        else:
            e_go, t_go, th = C.leg_cost(prev[0], prev[1], j, dj)
        e_ret, t_ret = C.to_depot(j, dj)
        need = e_go + C.work_E[j] + e_ret
        if need > rem and prev is not None:
            # close sortie: return to depot from prev, swap
            e_b, t_b = C.to_depot(prev[0], prev[1])
            E += e_b + m.E_swap; T += t_b + m.t_swap
            dist_transit += dist(C.end(*prev), C.depot)
            sorties.append(cur); cur = []
            rem = C.m.E_usable
            e_go, t_go = C.depot_to(j, dj); th = 0.0
            need = e_go + C.work_E[j] + e_ret
        if need > rem:
            feasible = False   # single swath does not fit a full battery
        rem -= e_go + C.work_E[j]
        E += e_go + C.work_E[j]; T += t_go + C.work_T[j]
        dist_transit += dist(C.depot, C.start(j, dj)) if prev is None or not cur else dist(C.end(*prev), C.start(j, dj))
        dist_work += C.sw[j].length; turns += th
        cur.append((j, dj)); prev = (j, dj)
    if prev is not None:
        e_b, t_b = C.to_depot(*prev)
        E += e_b; T += t_b; dist_transit += dist(C.end(*prev), C.depot)
        sorties.append(cur)
    return RouteResult(E, T, len(sorties), dist_work, dist_transit, turns, sorties, feasible)


if __name__ == "__main__":
    from fields import generate_synthetic
    from swaths import generate_swaths, best_angle
    f = generate_synthetic(3, seed=1)[2]
    sw = generate_swaths(f.polygon, 5.0, best_angle(f.polygon, 5.0))
    depot = (0.0, 0.0)
    C = Costs(sw, depot, UAVModel())
    # naive boustrophedon: row order, alternate direction
    order = [(s.idx, k % 2) for k, s in enumerate(sw)]
    r = evaluate_route(order, C)
    print(f"{f.id} {f.area_ha:.1f} ha, {len(sw)} swaths: E={r.energy_J/1e6:.2f} MJ, T={r.time_s/60:.1f} min, "
          f"sorties={r.n_sorties}, work={r.dist_work_m:.0f} m, transit={r.dist_transit_m:.0f} m, turns={r.total_turn_deg:.0f} deg, feasible={r.feasible}")
