"""Run baselines B1-B4 on a field set and save results.

    python experiments/run_baselines.py --fields data/thai_fields/thai_fields_utm48n_local.geojson \
        --out experiments/results/smoke_thai.csv --seeds 0 1 2 --ants 30 --iters 100 --fig figures/thai_example.png
"""
import argparse, csv, os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from fields import load_fields, load_split
from swaths import generate_swaths, best_angle
from energy import Costs, UAVModel, evaluate_route
from aco import ACO, ACOParams, boustrophedon
from heuristics import BASELINES

ap = argparse.ArgumentParser()
ap.add_argument("--fields", required=True)
ap.add_argument("--split"); ap.add_argument("--subset")
ap.add_argument("--out", required=True)
ap.add_argument("--seeds", type=int, nargs="+", default=[0])
ap.add_argument("--ants", type=int, default=30); ap.add_argument("--iters", type=int, default=100)
ap.add_argument("--width", type=float, default=5.0)
ap.add_argument("--uav"); ap.add_argument("--fig"); ap.add_argument("--fig_field")
ap.add_argument("--limit", type=int, default=0)
a = ap.parse_args()

ids = load_split(a.split)[a.subset] if a.split else None
fields = load_fields(a.fields, ids)
if a.limit: fields = fields[: a.limit]
uav = UAVModel.load(a.uav) if a.uav else UAVModel()
params = ACOParams(n_ants=a.ants, n_iters=a.iters)
os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)

rows = []
fig_done = False
for f in fields:
    ang = best_angle(f.polygon, a.width)
    sw = generate_swaths(f.polygon, a.width, ang)
    depot = (0.0, 0.0)        # bbox corner; same for every method
    C = Costs(sw, depot, uav)
    results = {}
    o, r = boustrophedon(C); results["B1_boustrophedon"] = r
    rows.append(dict(field_id=f.id, area_ha=round(f.area_ha, 2), n_swaths=len(sw), method="B1_boustrophedon", seed=-1,
                     energy_MJ=round(r.energy_J / 1e6, 4), time_min=round(r.time_s / 60, 2), sorties=r.n_sorties,
                     work_m=round(r.dist_work_m), transit_m=round(r.dist_transit_m), turn_deg=round(r.total_turn_deg), feasible=r.feasible, cpu_s=0.0))
    for name, h in BASELINES.items():
        for seed in a.seeds:
            t = time.time()
            o, r, info = ACO(params, h, seed=seed).run(C)
            rows.append(dict(field_id=f.id, area_ha=round(f.area_ha, 2), n_swaths=len(sw), method=name, seed=seed,
                             energy_MJ=round(r.energy_J / 1e6, 4), time_min=round(r.time_s / 60, 2), sorties=r.n_sorties,
                             work_m=round(r.dist_work_m), transit_m=round(r.dist_transit_m), turn_deg=round(r.total_turn_deg), feasible=r.feasible, cpu_s=round(time.time() - t, 1)))
            if seed == a.seeds[0]: results[name] = r
    print(f"{f.id:12s} {f.area_ha:5.1f} ha {len(sw):4d} swaths | " + " | ".join(f"{k[:2]} {v.energy_J/1e6:.2f}" for k, v in results.items()), flush=True)
    if a.fig and not fig_done and (a.fig_field is None or f.id == a.fig_field):
        from plotting import compare_figure
        os.makedirs(os.path.dirname(a.fig) or ".", exist_ok=True)
        compare_figure(f.polygon, C, results, a.fig, f"{f.id}  ({f.area_ha:.1f} ha, {len(sw)} swaths, width {a.width} m)")
        fig_done = True

with open(a.out, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print("saved", a.out, len(rows), "rows")
