"""MAX-MIN Ant System for swath ordering with battery sorties.

Nodes are (swath i, direction d) pairs -> 2n nodes. Pheromone tau[a][b] lives on node->node moves
(plus a virtual depot row). Every method shares this exact machinery; only `heuristic` differs.

    from aco import ACO, ACOParams
    res = ACO(ACOParams(), heuristic=h_distance, seed=0).run(C)   # C = energy.Costs
"""
from __future__ import annotations
import math, time
from dataclasses import dataclass, field
import numpy as np
from energy import Costs, evaluate_route, RouteResult, dist, heading, turn_angle_deg


@dataclass
class ACOParams:
    n_ants: int = 30
    n_iters: int = 150
    alpha: float = 1.0          # LOCKED 2026-10-13: grid {0.5,1,2}x{2,3,5}x{0.05,0.1,0.2} on validation -> (1, 3, 0.1) best
    beta: float = 3.0
    rho: float = 0.1            # evaporation
    p_best: float = 0.05        # MMAS tau_min derivation
    elitist_every: int = 5      # use global-best for update every k iterations, else iteration-best
    candidate_k: int = 0        # 0 = all candidates; >0 = nearest-k candidate list by distance (speed)
    time_limit_s: float = 0.0   # 0 = none
    local_search: bool = False  # 2-opt style or-opt on the swath order (same for all methods when on)
    greedy: bool = False        # deterministic constructive policy: always pick argmax of heuristic (no pheromone, no sampling)


class ACO:
    def __init__(self, params: ACOParams, heuristic, seed: int = 0, feature_mask=None):
        self.p, self.h, self.rng = params, heuristic, np.random.default_rng(seed)
        self.mask = feature_mask or (lambda d, t, l, e, dd, f: (d, t, l, e, dd, f))

    # ------------------------------------------------------------------ precompute
    def _prep(self, C: Costs):
        n = C.n; N = 2 * n
        self.n, self.N, self.C = n, N, C
        starts = np.array([C.start(i, d) for i in range(n) for d in range(2)])
        ends = np.array([C.end(i, d) for i in range(n) for d in range(2)])
        heads = np.array([C.head(i, d) for i in range(n) for d in range(2)])
        self.starts, self.ends, self.heads = starts, ends, heads
        self.len = np.array([C.sw[i].length for i in range(n) for _ in range(2)])
        self.workE = np.array([C.work_E[i] for i in range(n) for _ in range(2)])
        self.depot = np.array(C.depot)
        self.depot_dist_end = np.hypot(ends[:, 0] - self.depot[0], ends[:, 1] - self.depot[1])
        self.retE = C.m.P_transit * self.depot_dist_end / C.m.v_transit
        # distance from every node's end to every node's start, and turn angles
        dx = starts[None, :, 0] - ends[:, None, 0]; dy = starts[None, :, 1] - ends[:, None, 1]
        self.D = np.hypot(dx, dy)                                  # [from_node, to_node]
        h_leave = np.arctan2(dy, dx)
        h_leave = np.where(self.D > 1e-6, h_leave, heads[None, :])
        t1 = np.abs((h_leave - heads[:, None] + math.pi) % (2 * math.pi) - math.pi)
        t2 = np.abs((heads[None, :] - h_leave + math.pi) % (2 * math.pi) - math.pi)
        self.TURN = np.degrees(t1 + t2)
        m = C.m
        self.goE = m.P_transit * self.D / m.v_transit + m.P_hover * self.TURN / m.omega + m.c_turn * self.TURN / 180.0
        self.D0 = np.hypot(starts[:, 0] - self.depot[0], starts[:, 1] - self.depot[1])
        self.goE0 = m.P_transit * self.D0 / m.v_transit

    # ------------------------------------------------------------------ one ant
    def _construct(self, tau: np.ndarray, tau0: np.ndarray) -> list[tuple[int, int]]:
        n, N = self.n, self.N
        visited = np.zeros(n, bool)
        order = []
        cur = -1               # -1 = depot
        rem = self.C.m.E_usable
        a, b = self.p.alpha, self.p.beta
        for _ in range(n):
            cand = np.flatnonzero(~np.repeat(visited, 2))     # node ids of unvisited swaths
            if cur < 0:
                d = self.D0[cand]; t = np.zeros_like(d); goE = self.goE0[cand]; ph = tau0[cand]
            else:
                d = self.D[cur, cand]; t = self.TURN[cur, cand]; goE = self.goE[cur, cand]; ph = tau[cur, cand]
            if self.p.candidate_k and len(cand) > self.p.candidate_k:
                keep = np.argpartition(d, self.p.candidate_k)[: self.p.candidate_k]
                cand, d, t, goE, ph = cand[keep], d[keep], t[keep], goE[keep], ph[keep]
            need = goE + self.workE[cand] + self.retE[cand]
            fits = (need <= rem).astype(float)
            efrac = rem / self.C.m.E_usable
            feats = self.mask(d, t, self.len[cand], efrac, self.depot_dist_end[cand], fits)
            eta = np.asarray(self.h(*feats), float)
            eta = np.where(np.isfinite(eta) & (eta > 0), eta, 1e-9)
            if self.p.greedy:
                k = int(np.argmax(eta))
            else:
                w = (ph ** a) * (eta ** b)
                s = w.sum()
                k = self.rng.choice(len(cand), p=w / s) if s > 0 and np.isfinite(s) else self.rng.integers(len(cand))
            node = int(cand[k]); i, di = divmod(node, 2)
            # battery bookkeeping identical to energy.evaluate_route
            if need[k] > rem and cur >= 0:
                rem = self.C.m.E_usable
                rem -= self.goE0[node] + self.workE[node]
            else:
                rem -= goE[k] + self.workE[node]
            visited[i] = True; order.append((i, di)); cur = node
        return order

    # ------------------------------------------------------------------ local search (optional)
    def _or_opt(self, order, C, best):
        improved = True
        while improved:
            improved = False
            for i in range(len(order)):
                for j in range(len(order)):
                    if abs(i - j) < 1: continue
                    cand = order[:]; seg = cand.pop(i); cand.insert(j, seg)
                    r = evaluate_route(cand, C)
                    if r.energy_J < best.energy_J - 1e-6:
                        order, best, improved = cand, r, True
        return order, best

    # ------------------------------------------------------------------ main loop
    def run(self, C: Costs, log=None) -> tuple[list, RouteResult, dict]:
        self._prep(C)
        n, N, p = self.n, self.N, self.p
        if p.greedy:   # single deterministic construction
            tau = np.ones((N, N)); tau0 = np.ones(N)
            o = self._construct(tau, tau0); r = evaluate_route(o, C)
            return o, r, {"history": [r.energy_J], "iters": 1, "time_s": 0.0}
        # initial solution for tau_max: greedy nearest
        gb_order = None; gb = None
        tau_max = 1.0; tau = np.full((N, N), tau_max); tau0 = np.full(N, tau_max)
        hist = []; t_start = time.time()
        for it in range(p.n_iters):
            ib_order, ib = None, None
            for _ in range(p.n_ants):
                o = self._construct(tau, tau0)
                r = evaluate_route(o, C)
                if ib is None or r.energy_J < ib.energy_J:
                    ib_order, ib = o, r
            if p.local_search:
                ib_order, ib = self._or_opt(ib_order, C, ib)
            if gb is None or ib.energy_J < gb.energy_J:
                gb_order, gb = ib_order, ib
            # MMAS bounds
            tau_max = 1.0 / (p.rho * gb.energy_J)
            tau_min = tau_max * (1 - p.p_best ** (1 / n)) / ((n / 2 - 1) * p.p_best ** (1 / n)) if n > 2 else tau_max / 10
            tau_min = min(tau_min, tau_max)
            # evaporate + deposit
            tau *= (1 - p.rho); tau0 *= (1 - p.rho)
            use_order, use = (gb_order, gb) if (it % p.elitist_every == 0) else (ib_order, ib)
            dep = 1.0 / use.energy_J
            prev = -1
            for (i, d) in use_order:
                node = 2 * i + d
                if prev < 0: tau0[node] += dep
                else: tau[prev, node] += dep
                prev = node
            np.clip(tau, tau_min, tau_max, out=tau); np.clip(tau0, tau_min, tau_max, out=tau0)
            hist.append(gb.energy_J)
            if log and it % 10 == 0:
                log(f"it {it:4d} best {gb.energy_J/1e6:.3f} MJ sorties {gb.n_sorties}")
            if p.time_limit_s and time.time() - t_start > p.time_limit_s:
                break
        return gb_order, gb, {"history": hist, "iters": len(hist), "time_s": time.time() - t_start}


# ---------------------------------------------------------------------- B1 baseline
def boustrophedon(C: Costs) -> tuple[list, RouteResult]:
    """Row order, alternate direction; try both starting directions and both row orders, keep the best."""
    sw = C.sw
    rows = sorted(set(s.row for s in sw))
    best_o, best = None, None
    for rev in (False, True):
        for d0 in (0, 1):
            order = []
            rr = rows[::-1] if rev else rows
            for k, row in enumerate(rr):
                segs = [s for s in sw if s.row == row]
                d = (d0 + k) % 2
                segs.sort(key=lambda s: s.p0[0] + s.p0[1], reverse=bool(d))
                order += [(s.idx, d) for s in segs]
            r = evaluate_route(order, C)
            if best is None or r.energy_J < best.energy_J:
                best_o, best = order, r
    return best_o, best


if __name__ == "__main__":
    from fields import generate_synthetic
    from swaths import generate_swaths, best_angle
    from energy import UAVModel
    from heuristics import BASELINES
    f = generate_synthetic(3, seed=1)[2]
    sw = generate_swaths(f.polygon, 5.0, best_angle(f.polygon, 5.0))
    C = Costs(sw, (0.0, 0.0), UAVModel())
    o, r = boustrophedon(C)
    print(f"B1 boustrophedon: {r.energy_J/1e6:.3f} MJ, {r.n_sorties} sorties, {r.time_s/60:.1f} min")
    for name, h in BASELINES.items():
        t = time.time()
        o, r, info = ACO(ACOParams(n_ants=20, n_iters=60), h, seed=0).run(C)
        print(f"{name}: {r.energy_J/1e6:.3f} MJ, {r.n_sorties} sorties, {r.time_s/60:.1f} min, turns {r.total_turn_deg:.0f} deg, {time.time()-t:.1f}s")
