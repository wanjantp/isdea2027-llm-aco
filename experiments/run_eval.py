"""Evaluate heuristics (baselines + evolved files) on a field set with the full ACO budget and several seeds.

  # validation: evolved vs hand-designed
  python experiments/run_eval.py --fields data/fields2benchmark/fields2benchmark_local.geojson \
      --split data/fields2benchmark/split.json --subset validation \
      --heuristic P1_qwen7b=experiments/results/evolve/local_T3_s0/best_heuristic.py \
      --seeds 10 --ants 30 --iters 150 --workers 8 --out experiments/results/eval/validation_v1

  # noise check: same budget as evolution, several ACO seeds, on the training set
  python experiments/run_eval.py --fields data/synthetic/synthetic_train_seed0.geojson --baselines B2_distance \
      --seeds 5 --ants 15 --iters 40 --workers 8 --out experiments/results/eval/noise_check

Outputs <out>/runs.csv (one row per field x method x seed), <out>/summary.csv, <out>/stats.txt
"""
import argparse, csv, json, os, sys, time, pickle
import multiprocessing as mp
for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"): os.environ[k] = "1"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

ap = argparse.ArgumentParser()
ap.add_argument("--fields", required=True); ap.add_argument("--split"); ap.add_argument("--subset")
ap.add_argument("--heuristic", action="append", default=[], help="name=path/to/heuristic.py (repeatable)")
ap.add_argument("--baselines", default="B2_distance,B3_dist_turn,B4_dist_turn_battery", help="comma list, or 'none'")
ap.add_argument("--seeds", type=int, default=10); ap.add_argument("--ants", type=int, default=30); ap.add_argument("--iters", type=int, default=150)
ap.add_argument("--budgets", default="", help="comma list of ants x iters, e.g. 'greedy,1x1,3x3,5x10,15x40,30x150'; overrides --ants/--iters and sweeps")
ap.add_argument("--width", type=float, default=5.0); ap.add_argument("--uav", default="data/energy/uav_params.json")
ap.add_argument("--workers", type=int, default=8); ap.add_argument("--limit", type=int, default=0)
ap.add_argument("--out", required=True)
a = ap.parse_args()


def _job(args):
    fid, method, kind, src, seed, swaths, uav_path, ants, iters, budget = args
    import warnings; warnings.filterwarnings("ignore")
    import numpy as np; np.seterr(all="ignore")
    from energy import Costs, UAVModel
    from aco import ACO, ACOParams, boustrophedon
    from heuristics import BASELINES, load_heuristic_from_code
    C = Costs(swaths, (0.0, 0.0), UAVModel.load(uav_path))
    t0 = time.time()
    if kind == "b1":
        _, r = boustrophedon(C)
    else:
        fn = BASELINES[src] if kind == "baseline" else load_heuristic_from_code(open(src).read())
        _, r, _ = ACO(ACOParams(n_ants=ants, n_iters=iters, greedy=(budget == "greedy")), fn, seed=seed).run(C)
    return dict(field_id=fid, method=method, budget=budget, seed=seed, energy_MJ=r.energy_J / 1e6, time_min=r.time_s / 60, sorties=r.n_sorties,
                work_m=r.dist_work_m, transit_m=r.dist_transit_m, turn_deg=r.total_turn_deg, feasible=r.feasible, cpu_s=time.time() - t0)


def main():
    from fields import load_fields, load_split
    from swaths import generate_swaths, best_angle
    os.makedirs(a.out, exist_ok=True)
    ids = load_split(a.split)[a.subset] if a.split else None
    fields = load_fields(a.fields, ids)
    if a.limit: fields = fields[: a.limit]
    print(f"{len(fields)} fields; generating swaths ...", flush=True)
    sw = {f.id: generate_swaths(f.polygon, a.width, best_angle(f.polygon, a.width)) for f in fields}
    meta = {f.id: dict(area_ha=round(f.area_ha, 2), n_swaths=len(sw[f.id])) for f in fields}
    methods = [("B1_boustrophedon", "b1", None)]
    if a.baselines != "none":
        methods += [(b, "baseline", b) for b in a.baselines.split(",")]
    for h in a.heuristic:
        name, path = h.split("=", 1); methods.append((name, "file", path))
    budgets = [b.strip() for b in a.budgets.split(",") if b.strip()] or [f"{a.ants}x{a.iters}"]
    jobs = []
    for f in fields:
        for name, kind, src in methods:
            if kind == "b1":
                jobs.append((f.id, name, kind, src, 0, sw[f.id], a.uav, 1, 1, "none")); continue
            for b in budgets:
                ants, iters = (1, 1) if b == "greedy" else map(int, b.split("x"))
                for s in (range(a.seeds) if b != "greedy" else [0]):
                    jobs.append((f.id, name, kind, src, s, sw[f.id], a.uav, ants, iters, b))
    print(f"{len(jobs)} runs on {a.workers} workers", flush=True)
    rows, t0 = [], time.time()
    with mp.Pool(a.workers) as pool:
        for i, r in enumerate(pool.imap_unordered(_job, jobs, chunksize=2)):
            r.update(meta[r["field_id"]]); rows.append(r)
            if (i + 1) % 50 == 0: print(f"  {i+1}/{len(jobs)}  {(time.time()-t0)/60:.1f} min", flush=True)
    with open(os.path.join(a.out, "runs.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    for b in budgets:
        print(f"\n===== budget {b} =====")
        summarise([r for r in rows if r["budget"] in (b, "none")], methods, tag=b)


def summarise(rows, methods, tag=""):
    import numpy as np
    from collections import defaultdict
    try:
        from scipy.stats import wilcoxon, friedmanchisquare
    except ImportError:
        wilcoxon = friedmanchisquare = None
    E = defaultdict(lambda: defaultdict(list))    # E[method][field] -> list over seeds
    for r in rows: E[r["method"]][r["field_id"]].append(r["energy_MJ"])
    fields = sorted(E["B1_boustrophedon"])
    b1 = {f: E["B1_boustrophedon"][f][0] for f in fields}
    names = [m[0] for m in methods]
    per_field_mean = {m: np.array([np.mean(E[m][f]) for f in fields]) for m in names}
    per_field_best = {m: np.array([np.min(E[m][f]) for f in fields]) for m in names}
    ratio_mean = {m: per_field_mean[m] / np.array([b1[f] for f in fields]) for m in names}
    # seed-to-seed noise: std of ratio across seeds, averaged over fields
    noise = {m: float(np.mean([np.std(E[m][f]) / b1[f] for f in fields])) for m in names}
    lines = [f"fields={len(fields)}  seeds/method={len(E[names[-1]][fields[0]])}", ""]
    lines.append(f"{'method':28s} {'mean ratio to B1':>16s} {'std over fields':>15s} {'best-seed ratio':>15s} {'seed noise':>10s} {'mean sorties':>12s}")
    srt = defaultdict(list)
    for r in rows: srt[r["method"]].append(r["sorties"])
    for m in names:
        rb = per_field_best[m] / np.array([b1[f] for f in fields])
        lines.append(f"{m:28s} {ratio_mean[m].mean():16.4f} {ratio_mean[m].std():15.4f} {rb.mean():15.4f} {noise[m]:10.4f} {np.mean(srt[m]):12.2f}")
    lines.append("")
    if wilcoxon is not None and len(fields) >= 6:
        lines.append("Wilcoxon signed-rank (paired over fields, mean over seeds), H1: row < column")
        for mi in names[1:]:
            for mj in names[1:]:
                if mi == mj: continue
                d = per_field_mean[mi] - per_field_mean[mj]
                if np.allclose(d, 0): continue
                p = wilcoxon(per_field_mean[mi], per_field_mean[mj], alternative="less").pvalue
                wins = int((d < 0).sum())
                lines.append(f"  {mi:26s} < {mj:26s}  p={p:.4f}  wins {wins}/{len(fields)}  mean diff {100*d.mean()/np.mean([b1[f] for f in fields]):+.2f}% of B1")
        if friedmanchisquare is not None and len(names) > 3:
            fr = friedmanchisquare(*[per_field_mean[m] for m in names[1:]])
            lines.append(f"Friedman over {names[1:]}: chi2={fr.statistic:.2f} p={fr.pvalue:.4f}")
    txt = "\n".join(lines); print(txt)
    open(os.path.join(a.out, f"stats_{tag}.txt"), "w").write(txt + "\n")
    first = not os.path.exists(os.path.join(a.out, "summary.csv")) or tag == ""
    with open(os.path.join(a.out, "summary.csv"), "a" if not first else "w", newline="") as fh:
        w = csv.writer(fh)
        if first: w.writerow(["budget", "method", "mean_ratio_to_B1", "std_over_fields", "best_seed_ratio", "seed_noise", "mean_sorties"])
        for m in names:
            rb = per_field_best[m] / np.array([b1[f] for f in fields])
            w.writerow([tag, m, f"{ratio_mean[m].mean():.5f}", f"{ratio_mean[m].std():.5f}", f"{rb.mean():.5f}", f"{noise[m]:.5f}", f"{np.mean(srt[m]):.3f}"])


if __name__ == "__main__":
    mp.set_start_method("spawn", force=True)
    main()
