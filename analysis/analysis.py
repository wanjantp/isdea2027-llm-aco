"""All numbers quoted in the paper. Run from the repo root:  python analysis/analysis.py
Reads experiments/results/eval/{validation_*,test?_*}/runs.csv and writes analysis/numbers.json (+ prints a report).
B2* = distance-only ACO with eta = (1+d)^-k, k chosen per budget on the validation fields (k=1 is B2)."""
import os, json, glob
import numpy as np, pandas as pd
from scipy.stats import wilcoxon

HERE = os.path.dirname(os.path.abspath(__file__)); EVAL = os.path.join(HERE, "..", "experiments", "results", "eval")
BUD = ["greedy", "1x1", "3x3", "5x10", "15x40", "30x150"]; LOW = ["1x1", "3x3", "5x10"]
AI = {"1x1": 1, "3x3": 9, "5x10": 50, "15x40": 600, "30x150": 4500}
EVOLVED = ["coder7b", "q9b_T3rep", "q9b_T3", "q9b_T2", "q9b_T1", "q9b_api", "haiku", "luna", "sol"]
VAL_NAMES = {"local_qwen25coder7b_T3_v3_s0": "coder7b", "local_qwen35_9b_T3_v3_s1": "q9b_T3", "local_qwen35_9b_T3_repair_v3_s1": "q9b_T3rep",
             "local_qwen35_9b_T2_v3_s0": "q9b_T2", "local_qwen35_9b_T1_v3_s2": "q9b_T1", "or_gpt6sol_T3_v3_s0": "sol",
             "or_gpt6luna_T3_v3_s1": "luna", "or_haiku55_T3_v3_s0": "haiku", "or_qwen35_9b_T3_v3_s0": "q9b_api"}


def load(prefix_globs):
    rs = [pd.read_csv(f) for g in prefix_globs for f in glob.glob(os.path.join(EVAL, g, "runs.csv"))]
    return pd.concat(rs, ignore_index=True)


def per_field(r):
    b1 = r[r.method == "B1_boustrophedon"].groupby("field_id").energy_MJ.mean()
    r = r[r.method != "B1_boustrophedon"]
    f = r.groupby(["budget", "method", "field_id"]).agg(E=("energy_MJ", "mean"), T=("time_min", "mean"), cpu=("cpu_s", "mean"),
                                                        S=("sorties", "mean")).reset_index()
    f["rB1"] = f.E / f.field_id.map(b1)
    return f


def holm(p):
    p = np.asarray(p, float); n = len(p); order = np.argsort(p); adj = np.empty(n); run = 0
    for i, j in enumerate(order):
        run = max(run, (n - i) * p[j]); adj[j] = min(1.0, run)
    return adj


def main():
    out = {}
    # ---------------- validation: select k per budget
    val = per_field(load(["validation_beta_control", "validation_k_ext"]))
    ks = {"B2_distance": 1.0, "B2_k1.5": 1.5, "B2_k2": 2.0, "B2_k3": 3.0, "B2_k4": 4.0, "B2_k5": 5.0, "B2_k6": 6.0, "B2_k8": 8.0}
    avail = [m for m in ks if m in set(val.method)]
    sel = {}
    for b in ["1x1", "3x3", "5x10"]:
        m = val[(val.budget == b) & val.method.isin(avail)].groupby("method").rB1.mean()
        sel[b] = m.idxmin(); out[f"val_k_curve_{b}"] = {k: round(float(v), 4) for k, v in m.items()}
    sel["15x40"] = sel["30x150"] = sel["greedy"] = "B2_distance"   # beta was tuned at a full budget (30x100)
    out["k_grid"] = sorted(ks[m] for m in avail); out["k_selected"] = {b: ks[sel[b]] for b in sel}

    # ---------------- tests
    sets = {}
    for t in ["testA", "testB", "testC"]:
        f = per_field(load([f"{t}_v3", f"{t}_beta", f"{t}_k_ext"])); f["set"] = t; f["key"] = t + "/" + f.field_id; sets[t] = f
    F = pd.concat(sets.values())
    star = [F[(F.budget == b) & (F.method == m)].assign(method="B2star") for b, m in sel.items()]
    F = pd.concat([F] + star)

    def pv(d, m, base):
        p = d.pivot(index="key", columns="method", values="E"); x, y = p[m], p[base]
        dif = float(((x / y - 1) * 100).mean())
        try: pval = float(wilcoxon(x, y, alternative="less").pvalue); pgt = float(wilcoxon(x, y, alternative="greater").pvalue)
        except ValueError: pval = pgt = 1.0
        return dif, int((x < y).sum()), len(x), pval, pgt

    rows = ["B3_dist_turn", "B4_dist_turn_battery", "B2star"] + EVOLVED
    table = {}
    for b in BUD[1:]:
        d = F[F.budget == b]
        res = {m: pv(d, m, "B2_distance") for m in rows}
        resS = {m: pv(d, m, "B2star") for m in EVOLVED}
        hB = dict(zip(res, holm([res[m][3] for m in res]))); hS = dict(zip(resS, holm([resS[m][3] for m in resS])))
        # opposite direction (planner uses MORE energy), same families, Holm-corrected
        wB = dict(zip(res, holm([res[m][4] for m in res]))); wS = dict(zip(resS, holm([resS[m][4] for m in resS])))
        for m in rows:
            dif, w, n, p, _ = res[m]
            cell = {"vsB2": round(dif, 2), "winsB2": w, "n": n, "p_holm_B2": hB[m], "p_holm_B2_worse": wB[m]}
            if m in resS:
                d2, w2, _, p2, _ = resS[m]; cell.update({"vsB2star": round(d2, 2), "winsB2star": w2, "p_raw_B2star": p2, "p_holm_B2star": hS[m],
                                                         "p_holm_B2star_worse": wS[m]})
            table.setdefault(m, {})[b] = cell
    out["pooled"] = table

    # per-set key comparison: each evolved vs B2* at low budgets
    per = {}
    for t in sets:
        d = F[F.set == t]
        for b in LOW:
            for m in EVOLVED:
                dif, w, n, p, _ = pv(d[d.budget == b], m, "B2star"); per.setdefault(t, {}).setdefault(m, {})[b] = [round(dif, 2), w, n, p]
    out["per_set_vs_B2star"] = per

    # B2 vs boustrophedon at full budget, flight time, sorties
    out["B2_full_vs_B1"] = {t: round(float(sets[t][(sets[t].method == "B2_distance") & (sets[t].budget == "30x150")].rB1.mean()), 4) for t in sets}
    cpuB2 = F[F.method == "B2_distance"].groupby("budget").cpu.mean()
    out["cpu_B2_s"] = {b: round(float(cpuB2[b]), 3) for b in BUD}
    cpu_rel = F[F.budget.isin(LOW)].groupby("method").cpu.mean() / F[(F.budget.isin(LOW)) & (F.method == "B2_distance")].cpu.mean()
    out["cpu_per_run_rel_B2_low"] = {m: round(float(cpu_rel[m]), 2) for m in EVOLVED + ["B2star"] if m in cpu_rel}

    # equivalent compute: constructions and CPU seconds B2 (default) or B2 with the k selected at 3x3 need to match an evolved heuristic
    def equiv(t, m, b, ref):
        d = sets[t]; c = d.groupby(["method", "budget"]).agg(rB1=("rB1", "mean"), cpu=("cpu", "mean"))
        xs = [AI[x] for x in AI]; es = [c.loc[(ref, x), "rB1"] for x in AI]; cs = [c.loc[(ref, x), "cpu"] for x in AI]
        e = c.loc[(m, b), "rB1"]; mc = c.loc[(m, b), "cpu"]
        for i in range(len(xs) - 1):
            if es[i] >= e >= es[i + 1]:
                tt = (es[i] - e) / (es[i] - es[i + 1])
                n = 10 ** (np.log10(xs[i]) + tt * (np.log10(xs[i + 1]) - np.log10(xs[i])))
                s = 10 ** (np.log10(cs[i]) + tt * (np.log10(cs[i + 1]) - np.log10(cs[i])))
                return round(float(n / AI[b]), 1), round(float(s / mc), 1)
        return (None, None) if e < min(es) else (0.0, 0.0)
    ref_star = sel["3x3"]
    have_ref = all(((ref_star, x) in set(zip(sets["testA"].method, sets["testA"].budget))) for x in AI)
    eq = {}
    for t in sets:
        for m in ["coder7b", "sol", "q9b_T2"]:
            eq.setdefault(t, {})[m] = {"vs_B2_constr_x": equiv(t, m, "3x3", "B2_distance")[0], "vs_B2_cpu_x": equiv(t, m, "3x3", "B2_distance")[1]}
            if have_ref:
                a = equiv(t, m, "3x3", ref_star); eq[t][m].update({f"vs_{ref_star}_constr_x": a[0], f"vs_{ref_star}_cpu_x": a[1]})
    out["equiv_3x3"] = eq

    # flight time saved (coder vs B2 and vs B2*) on Test-C and Test-A
    ft = {}
    for t in sets:
        for b in ["1x1", "3x3"]:
            d = F[(F.set == t) & (F.budget == b)].pivot(index="key", columns="method", values="T")
            ft[f"{t}_{b}"] = {"vs_B2_s": round(float((d.B2_distance - d.coder7b).mean() * 60), 0),
                              "vs_B2star_s": round(float((d.B2star - d.coder7b).mean() * 60), 0), "mission_min": round(float(d.B2_distance.mean()), 1)}
    out["flight_time_coder"] = ft

    # validation selection row: test vs B2* at 3x3 for Table 4
    out["table4_test_vs_B2star_3x3"] = {m: table[m]["3x3"]["vsB2star"] for m in EVOLVED}
    out = review(out)
    json.dump(out, open(os.path.join(HERE, "numbers.json"), "w"), indent=1, default=float)
    return out


# ---------------------------------------------------------------- review additions (2026-10-16): CIs, medians, run-level, knock-out, sensitivity
RUN_MAP = {"local_qwen25coder7b_T3": "coder7b", "local_qwen35_9b_T1": "q9b_T1", "local_qwen35_9b_T2": "q9b_T2",
           "local_qwen35_9b_T3_repair": "q9b_T3rep", "local_qwen35_9b_T3": "q9b_T3", "or_qwen35_9b_T3": "q9b_api",
           "or_haiku55_T3": "haiku", "or_gpt6luna_T3": "luna", "or_gpt6sol_T3": "sol"}


def hodges_lehmann(x):
    x = np.asarray(x); w = (x[:, None] + x[None, :]) / 2.0
    return float(np.median(w[np.triu_indices(len(x))]))


def boot_ci(x, stat=np.mean, n=4000, seed=0):
    rng = np.random.default_rng(seed); x = np.asarray(x)
    b = np.array([stat(x[rng.integers(0, len(x), len(x))]) for _ in range(n)])
    return [round(float(v), 3) for v in np.percentile(b, [2.5, 97.5])]


def review(out):
    sel = {"1x1": "B2_k8", "3x3": "B2_k5", "5x10": "B2_k2", "15x40": "B2_distance", "30x150": "B2_distance"}
    R = []
    for t in ["testA", "testB", "testC"]:
        r = load([f"{t}_v3", f"{t}_beta", f"{t}_k_ext"]); r["set"] = t; R.append(r)
    R = pd.concat(R); R["key"] = R.set + "/" + R.field_id
    ev = {}
    for b in ["1x1", "3x3", "5x10", "15x40"]:
        d = R[R.budget == b].groupby(["key", "method"]).energy_MJ.mean().unstack()
        for m in EVOLVED:
            x = (d[m] / d[sel[b]] - 1) * 100; y = (d[m] / d["B2_distance"] - 1) * 100
            ev.setdefault(m, {})[b] = {"vsB2star_mean": round(float(x.mean()), 3), "ci_mean": boot_ci(x), "median": round(float(x.median()), 3),
                                       "ci_median": boot_ci(x, np.median), "HL": round(hodges_lehmann(x.values), 3), "sd_fields": round(float(x.std()), 3),
                                       "frac_improved": round(float((x < 0).mean()), 3), "vsB2_mean": round(float(y.mean()), 3), "ci_vsB2": boot_ci(y)}
            for t in ["testA", "testB", "testC"]:
                xt = x[x.index.str.startswith(t)]
                ev[m][b][t] = {"mean": round(float(xt.mean()), 3), "ci": boot_ci(xt), "n": int(len(xt))}
    out["effects_vs_B2star"] = ev
    # Bonferroni over all tests reported in Table 3 (~5 budgets x 2 baselines x planners)
    ntests = sum(1 for m in out["pooled"] for b in out["pooled"][m] for k in ("p_holm_B2", "p_holm_B2star") if k in out["pooled"][m][b])
    out["n_tests_table3"] = ntests
    # error analysis: gain vs number of swaths
    from scipy.stats import spearmanr
    meta = R.groupby("key").n_swaths.first()
    d = R[R.budget == "3x3"].groupby(["key", "method"]).energy_MJ.mean().unstack()
    g_b2 = (d.coder7b / d.B2_distance - 1) * 100; g_st = (d.coder7b / d[sel["3x3"]] - 1) * 100
    out["error_analysis_3x3"] = {"spearman_gain_vsB2_vs_swaths": [round(float(v), 4) for v in spearmanr(g_b2, meta.loc[g_b2.index])],
                                 "spearman_gain_vsB2star_vs_swaths": [round(float(v), 4) for v in spearmanr(g_st, meta.loc[g_st.index])],
                                 "worst_vsB2star": {k: round(float(v), 2) for k, v in g_st.sort_values().tail(3).items()},
                                 "best_vsB2star": {k: round(float(v), 2) for k, v in g_st.sort_values().head(3).items()}}
    seedcv = R[(R.budget == "3x3") & R.method.isin(["B2_k5", "coder7b"])].groupby(["key", "method"]).energy_MJ.agg(lambda x: x.std() / x.mean() * 100)
    out["seed_cv_3x3_pct"] = round(float(seedcv.mean()), 3)

    # run-level (all 27 runs) if available
    if glob.glob(os.path.join(EVAL, "testA_allruns", "runs.csv")):
        A = []
        for t in ["testA", "testB", "testC"]:
            a = load([f"{t}_allruns"]); a["set"] = t; A.append(a)
        A = pd.concat(A); A["key"] = A.set + "/" + A.field_id
        base = R[R.method.isin(["B2_k5", "B2_k2", "B2_distance"])]
        A = pd.concat([A, base])
        runlvl = {}
        for b in ["3x3", "5x10"]:
            d = A[A.budget == b].groupby(["key", "method"]).energy_MJ.mean().unstack()
            for col in d.columns:
                if not col.endswith(tuple(f"_s{i}" for i in range(5))): continue
                g = RUN_MAP[col.rsplit("_v3_s", 1)[0]]
                x = (d[col] / d[sel[b]] - 1) * 100
                runlvl.setdefault(g, {}).setdefault(b, []).append(round(float(x.mean()), 3))
            for col in ["coder7b_noturn", "q9b_T2_noturn", "q9b_T3_noturn"]:
                if col in d:
                    x = (d[col] / d[sel[b]] - 1) * 100
                    out.setdefault("knockout", {}).setdefault(col, {})[b] = {"vsB2star_mean": round(float(x.mean()), 3), "ci": boot_ci(x)}
        out["run_level_vsB2star"] = {g: {b: {"runs": v, "mean": round(float(np.mean(v)), 4), "sd": round(float(np.std(v, ddof=1)), 4) if len(v) > 1 else None}
                                         for b, v in bb.items()} for g, bb in runlvl.items()}
        # run-level comparison local vs API (Mann-Whitney on run means at 3x3 and 5x10)
        from scipy.stats import mannwhitneyu
        for b in ["3x3", "5x10"]:
            loc = [v for g in ["coder7b", "q9b_T1", "q9b_T2", "q9b_T3", "q9b_T3rep"] for v in runlvl.get(g, {}).get(b, [])]
            api = [v for g in ["luna", "haiku", "sol", "q9b_api"] for v in runlvl.get(g, {}).get(b, [])]
            if loc and api:
                out.setdefault("local_vs_api_runs", {})[b] = {"local_mean": round(float(np.mean(loc)), 3), "api_mean": round(float(np.mean(api)), 3),
                                                             "n_local": len(loc), "n_api": len(api), "p_mwu_two_sided": float(mannwhitneyu(loc, api).pvalue)}
    # c_turn sensitivity if available
    for c in ["05", "2"]:
        f = os.path.join(EVAL, f"testA_cturn_x{c}", "runs.csv")
        if os.path.exists(f):
            r = pd.read_csv(f)
            for b in ["3x3", "5x10"]:
                d = r[r.budget == b].groupby(["field_id", "method"]).energy_MJ.mean().unstack()
                ref = "B2_k5" if b == "3x3" else "B2_k2"
                res = {}
                for m in ["coder7b", "q9b_T2", "q9b_T3", ref]:
                    x = (d[m] / d["B2_distance"] - 1) * 100; res[m + "_vsB2"] = round(float(x.mean()), 3)
                for m in ["coder7b", "q9b_T2", "q9b_T3"]:
                    x = (d[m] / d[ref] - 1) * 100
                    try: p = float(wilcoxon(d[m], d[ref], alternative="less").pvalue)
                    except ValueError: p = 1.0
                    res[m + "_vsB2star"] = [round(float(x.mean()), 3), boot_ci(x), p]
                out.setdefault("cturn_sensitivity", {}).setdefault(f"x{c}", {})[b] = res
    return out


ALPHA = 0.025  # per direction; both one-sided tests together = two-sided alpha 0.05

if __name__ == "__main__":
    o = main()
    print("k grid", o["k_grid"], "selected", o["k_selected"])
    for b in ["1x1", "3x3", "5x10"]: print(" val", b, o[f"val_k_curve_{b}"])
    print("\npooled vs B2 (Holm *) / vs B2* (Holm dagger)")
    for m, d in o["pooled"].items():
        s = []
        for b in BUD[1:]:
            c = d[b]; mk = ("*" if c["p_holm_B2"] < ALPHA and c["vsB2"] < 0 else "") + ("†" if c.get("p_holm_B2star", 1) < ALPHA and c.get("vsB2star", 0) < 0 else "")
            s.append(f"{c['vsB2']:+.2f}{mk:2s}" + (f"({c['vsB2star']:+.2f} p={c['p_raw_B2star']:.0e})" if "vsB2star" in c else ""))
        print(f"{m:22s}", " ".join(f"{x:>24s}" for x in s))
    print("\nper set coder7b vs B2*:", {t: o["per_set_vs_B2star"][t]["coder7b"] for t in o["per_set_vs_B2star"]})
    print("cpu rel", o["cpu_per_run_rel_B2_low"]); print("cpu B2", o["cpu_B2_s"]); print("equiv", json.dumps(o["equiv_3x3"]))
    print("flight", o["flight_time_coder"]); print("B2 full", o["B2_full_vs_B1"])
