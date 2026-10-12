"""Grid-tune hand-designed baseline weights (B3 w_turn, B4 w_turn+w_depot) and ACO alpha/beta/rho on the VALIDATION set.
Run once, then lock the values in heuristics.py / ACOParams and never touch them again.

  python experiments/tune_baselines.py --fields data/fields2benchmark/fields2benchmark_local.geojson \
      --split data/fields2benchmark/split.json --subset validation --limit 25 --seeds 3 --workers 8 \
      --out experiments/results/tune
"""
import argparse, csv, itertools, json, os, sys, time
import multiprocessing as mp
for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"): os.environ[k] = "1"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

ap = argparse.ArgumentParser()
ap.add_argument("--fields", required=True); ap.add_argument("--split"); ap.add_argument("--subset")
ap.add_argument("--seeds", type=int, default=3); ap.add_argument("--ants", type=int, default=30); ap.add_argument("--iters", type=int, default=100)
ap.add_argument("--width", type=float, default=5.0); ap.add_argument("--uav", default="data/energy/uav_params.json")
ap.add_argument("--workers", type=int, default=8); ap.add_argument("--limit", type=int, default=25)
ap.add_argument("--stage", default="all", choices=["all", "weights", "aco"])
ap.add_argument("--out", required=True)
a = ap.parse_args()

W_TURN = [0.0, 0.05, 0.1, 0.25, 0.5, 1.0]
W_DEPOT = [0.0, 0.25, 0.5, 1.0, 2.0]
ACO_GRID = {"alpha": [0.5, 1.0, 2.0], "beta": [2.0, 3.0, 5.0], "rho": [0.05, 0.1, 0.2]}


def _job(args):
    fid, label, hname, hkw, aco_kw, seed, swaths, uav_path, ants, iters = args
    import warnings; warnings.filterwarnings("ignore")
    import numpy as np; np.seterr(all="ignore")
    from functools import partial
    from energy import Costs, UAVModel
    from aco import ACO, ACOParams, boustrophedon
    import heuristics as H
    C = Costs(swaths, (0.0, 0.0), UAVModel.load(uav_path))
    if hname == "B1":
        _, r = boustrophedon(C); return dict(field_id=fid, label=label, seed=seed, energy_MJ=r.energy_J / 1e6)
    fn = partial(getattr(H, hname), **hkw)
    _, r, _ = ACO(ACOParams(n_ants=ants, n_iters=iters, **aco_kw), fn, seed=seed).run(C)
    return dict(field_id=fid, label=label, seed=seed, energy_MJ=r.energy_J / 1e6)


def run(jobs, tag):
    import numpy as np
    from collections import defaultdict
    print(f"[{tag}] {len(jobs)} runs", flush=True)
    rows = []
    t0 = time.time()
    with mp.Pool(a.workers) as pool:
        for i, r in enumerate(pool.imap_unordered(_job, jobs, chunksize=2)):
            rows.append(r)
            if (i + 1) % 100 == 0: print(f"  {i+1}/{len(jobs)} {(time.time()-t0)/60:.1f} min", flush=True)
    E = defaultdict(lambda: defaultdict(list))
    for r in rows: E[r["label"]][r["field_id"]].append(r["energy_MJ"])
    b1 = {f: v[0] for f, v in E["B1"].items()}
    res = {lab: float(np.mean([np.mean(v) / b1[f] for f, v in d.items()])) for lab, d in E.items() if lab != "B1"}
    with open(os.path.join(a.out, f"{tag}_runs.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    return res


def main():
    from fields import load_fields, load_split
    from swaths import generate_swaths, best_angle
    os.makedirs(a.out, exist_ok=True)
    ids = load_split(a.split)[a.subset] if a.split else None
    fields = load_fields(a.fields, ids)[: a.limit]
    sw = {f.id: generate_swaths(f.polygon, a.width, best_angle(f.polygon, a.width)) for f in fields}
    base = [(f.id, "B1", "B1", {}, {}, 0, sw[f.id], a.uav, a.ants, a.iters) for f in fields]
    result = {}
    if a.stage in ("all", "weights"):
        jobs = list(base)
        for f in fields:
            for s in range(a.seeds):
                jobs.append((f.id, "B2", "h_distance", {}, {}, s, sw[f.id], a.uav, a.ants, a.iters))
                for wt in W_TURN:
                    jobs.append((f.id, f"B3_wt{wt}", "h_dist_turn", {"w_turn": wt}, {}, s, sw[f.id], a.uav, a.ants, a.iters))
                for wt, wd in itertools.product(W_TURN, W_DEPOT):
                    jobs.append((f.id, f"B4_wt{wt}_wd{wd}", "h_dist_turn_battery", {"w_turn": wt, "w_depot": wd}, {}, s, sw[f.id], a.uav, a.ants, a.iters))
        res = run(jobs, "weights")
        for k, v in sorted(res.items(), key=lambda kv: kv[1]): print(f"  {k:22s} {v:.4f}")
        b3 = min((k for k in res if k.startswith("B3")), key=res.get); b4 = min((k for k in res if k.startswith("B4")), key=res.get)
        result["weights"] = {"B2": res["B2"], "best_B3": (b3, res[b3]), "best_B4": (b4, res[b4]), "all": res}
        print(f"best B3: {b3} {res[b3]:.4f} | best B4: {b4} {res[b4]:.4f} | B2 {res['B2']:.4f}")
    if a.stage in ("all", "aco"):
        jobs = list(base)
        for f in fields:
            for s in range(a.seeds):
                for al, be, rh in itertools.product(ACO_GRID["alpha"], ACO_GRID["beta"], ACO_GRID["rho"]):
                    jobs.append((f.id, f"a{al}_b{be}_r{rh}", "h_distance", {}, {"alpha": al, "beta": be, "rho": rh}, s, sw[f.id], a.uav, a.ants, a.iters))
        res = run(jobs, "aco")
        for k, v in sorted(res.items(), key=lambda kv: kv[1])[:8]: print(f"  {k:22s} {v:.4f}")
        best = min(res, key=res.get); result["aco"] = {"best": (best, res[best]), "all": res}
        print(f"best ACO params (with B2 heuristic): {best} {res[best]:.4f}")
    json.dump(result, open(os.path.join(a.out, "tuning_result.json"), "w"), indent=1)


if __name__ == "__main__":
    mp.set_start_method("spawn", force=True)
    main()
