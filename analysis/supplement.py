"""Supplementary material for the ISDEA 2027 paper. Run from the repo root after analysis/analysis.py:
    python analysis/supplement.py   ->  supplement/supplement.md + figures
Tables: effects vs B2* with bootstrap CIs (pooled and per test set), run-level results, turn knock-outs, c_turn sensitivity;
Figure S1: per-field gain of the best heuristic vs field size."""
import os, json
import pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__)); EVAL = os.path.join(HERE, "..", "experiments", "results", "eval")
OUT = os.path.join(HERE, "..", "supplement"); os.makedirs(OUT, exist_ok=True)
N = json.load(open(os.path.join(HERE, "numbers.json")))
NAMES = {"coder7b": "qwen2.5-coder:7b (T3)", "q9b_T3rep": "qwen3.5:9b (T3+repair)", "q9b_T3": "qwen3.5:9b (T3)", "q9b_T2": "qwen3.5:9b (T2)",
         "q9b_T1": "qwen3.5:9b (T1)", "q9b_api": "qwen3.5-9b API (T3)", "haiku": "claude-haiku-5.5 (T3)", "luna": "gpt-6-luna (T3)", "sol": "gpt-6-sol (T3)"}
L = ["# Supplementary material", "",
     "All values: energy of the selected evolved heuristic relative to the budget-tuned control B2* (%, negative = less energy), "
     "fields as the unit (mean over 10 ACO seeds per field). 95 % CIs: percentile bootstrap over fields (4000 resamples). "
     "HL = Hodges-Lehmann median of paired differences. B2* uses k = 8 (1x1), 5 (3x3), 2 (5x10), 1 (15x40), selected on validation.", ""]

L += ["## S1. Effects versus B2* on the 128 test fields", "",
      "| Heuristic | Budget | Mean | 95 % CI (mean) | Median | 95 % CI (median) | HL | Fields improved | SD over fields |", "|---|---|---|---|---|---|---|---|---|"]
for m, bb in N["effects_vs_B2star"].items():
    for b in ["1x1", "3x3", "5x10", "15x40"]:
        c = bb[b]
        L.append(f"| {NAMES[m]} | {b} | {c['vsB2star_mean']:+.2f} | [{c['ci_mean'][0]:+.2f}, {c['ci_mean'][1]:+.2f}] | {c['median']:+.2f} | "
                 f"[{c['ci_median'][0]:+.2f}, {c['ci_median'][1]:+.2f}] | {c['HL']:+.2f} | {100 * c['frac_improved']:.0f} % | {c['sd_fields']:.2f} |")
L += ["", "## S2. Per test set (mean versus B2*, 95 % CI)", "", "| Heuristic | Budget | Test-A (n=100) | Test-B (n=8) | Test-C (n=20) |", "|---|---|---|---|---|"]
for m, bb in N["effects_vs_B2star"].items():
    for b in ["3x3", "5x10", "15x40"]:
        c = bb[b]
        cells = [f"{c[t]['mean']:+.2f} [{c[t]['ci'][0]:+.2f}, {c[t]['ci'][1]:+.2f}]" for t in ["testA", "testB", "testC"]]
        L.append(f"| {NAMES[m]} | {b} | " + " | ".join(cells) + " |")

if "run_level_vsB2star" in N:
    L += ["", "## S3. Run level: every evolution run on the 128 test fields (mean energy vs B2*, %)", "",
          "| Configuration | Budget | Runs | Run means | Mean | SD |", "|---|---|---|---|---|---|"]
    for g, bb in N["run_level_vsB2star"].items():
        for b, c in bb.items():
            sd = "-" if c["sd"] is None else f"{c['sd']:.2f}"
            L.append(f"| {NAMES[g]} | {b} | {len(c['runs'])} | {', '.join(f'{v:+.2f}' for v in c['runs'])} | {c['mean']:+.2f} | {sd} |")
    if "local_vs_api_runs" in N:
        L += ["", "Local (qwen2.5-coder, qwen3.5 T1-T3, repair) versus API (luna, haiku, sol, parity) runs, two-sided Mann-Whitney on run means:", ""]
        for b, c in N["local_vs_api_runs"].items():
            L.append(f"- {b}: local {c['local_mean']:+.2f} % (n={c['n_local']}), API {c['api_mean']:+.2f} % (n={c['n_api']}), p = {c['p_mwu_two_sided']:.3f}")
if "knockout" in N:
    L += ["", "## S4. Turn-term knock-out (same programs with the turn factor set to 1), mean vs B2* [95 % CI]", "",
          "| Program | 3x3 | 5x10 |", "|---|---|---|"]
    full = N["effects_vs_B2star"]
    for k, c in N["knockout"].items():
        m = k.replace("_noturn", "")
        L.append(f"| {NAMES[m]} with turn term | {full[m]['3x3']['vsB2star_mean']:+.2f} | {full[m]['5x10']['vsB2star_mean']:+.2f} |")
        L.append(f"| {NAMES[m]} without turn term | {c['3x3']['vsB2star_mean']:+.2f} [{c['3x3']['ci'][0]:+.2f}, {c['3x3']['ci'][1]:+.2f}] | "
                 f"{c['5x10']['vsB2star_mean']:+.2f} [{c['5x10']['ci'][0]:+.2f}, {c['5x10']['ci'][1]:+.2f}] |")
if "cturn_sensitivity" in N:
    L += ["", "## S5. Sensitivity to the U-turn cost (Test-A, 100 fields; k of B2* not re-selected)", "",
          "| c_turn | Budget | Heuristic | vs B2 | vs B2* [95 % CI] | Wilcoxon p (one-sided) |", "|---|---|---|---|---|---|"]
    for c, bb in N["cturn_sensitivity"].items():
        for b, r in bb.items():
            for m in ["coder7b", "q9b_T2", "q9b_T3"]:
                v = r[m + "_vsB2star"]
                L.append(f"| {c} | {b} | {NAMES[m]} | {r[m + '_vsB2']:+.2f} | {v[0]:+.2f} [{v[1][0]:+.2f}, {v[1][1]:+.2f}] | {v[2]:.1e} |")

ea = N["error_analysis_3x3"]
L += ["", "## S6. Error analysis (3x3, qwen2.5-coder:7b heuristic)", "",
      f"- Gain over B2 (full-budget β) grows with field size: Spearman rho = {ea['spearman_gain_vsB2_vs_swaths'][0]:+.2f} with the number of swaths (p = {ea['spearman_gain_vsB2_vs_swaths'][1]:.1e}).",
      f"- The residual over B2* does not depend on size: rho = {ea['spearman_gain_vsB2star_vs_swaths'][0]:+.2f} (p = {ea['spearman_gain_vsB2star_vs_swaths'][1]:.2f}).",
      f"- Largest gains over B2*: {', '.join(f'{k} {v:+.2f} %' for k, v in ea['best_vsB2star'].items())}; largest losses: {', '.join(f'{k} {v:+.2f} %' for k, v in ea['worst_vsB2star'].items())}.",
      f"- Within-field seed variability at 3x3: coefficient of variation {N['seed_cv_3x3_pct']:.2f} % per run (standard error with 10 seeds about {N['seed_cv_3x3_pct'] / 10 ** 0.5:.2f} %).",
      "", "![Figure S1](fig_s1_error_analysis.png)", "",
      "Figure S1. Per-field energy change of the qwen2.5-coder:7b heuristic at 3x3 versus field size, relative to B2 with full-budget β (left) and to the budget-tuned B2* (right).", "",
      "## S7. Statistical notes", "",
      "- Table 2 of the paper reports one-sided Wilcoxon tests in both directions (less and more energy), in families of 12 planners (vs B2) and 9 (vs B2*) per budget and direction, 87 distinct comparisons per direction (B2* = B2 at 15x40 and 30x150). Holm correction is applied within each family, and each direction is tested at Holm-corrected p < 0.025, so the pair of one-sided tests corresponds to a two-sided test at alpha = 0.05. "
      "The main 'less energy' claims also hold under Bonferroni correction over the 87 comparisons (raw p < 0.025/87) except qwen3.5:9b T3+repair and T2 at 5x10 against B2* (raw p = 8e-4 and 5e-4).",
      "- CPU times are single-core times measured while 16 evaluation workers ran in parallel on one server; ratios are indicative and depend on the Python implementation.",
      "- Equivalent-compute ratios interpolate the mean energy-budget curve log-linearly between five budgets and carry no uncertainty estimate."]
NV = os.path.join(OUT, "noise_v2.json")
if os.path.exists(NV):
    import numpy as np
    d = json.load(open(NV)); ref = d["ref"]; R2 = d["res"]; ids = list(ref)
    fit = lambda n, ss: float(np.mean([np.mean([R2[n][str(s)][f] for s in ss]) / ref[f] for f in ids]))
    lab = {"B2": "seed heuristic (B2)", "k5": "k = 5 control (B2*)", "coder7b": NAMES["coder7b"], "q9b_T3": NAMES["q9b_T3"]}
    L += ["", "## S8. Noise of the training fitness (train_v2, T25 parameters, ACO 3x3, 30 fields)", "",
          "Evolution scored every program on ACO seeds 0-2. Re-scoring on seeds 3-14 (four further triples) gives:", "",
          "| Program | Fitness, seeds 0-2 | Fitness, seeds 3-14 | Change | SD over 5 triples (rel.) | vs k = 5, seeds 0-14 |", "|---|---|---|---|---|---|"]
    for n in ["B2", "k5", "coder7b", "q9b_T3"]:
        a, b = fit(n, range(3)), fit(n, range(3, 15)); tr = [fit(n, range(3 * j, 3 * j + 3)) for j in range(5)]
        L.append(f"| {lab[n]} | {a:.4f} | {b:.4f} | {100 * (b / a - 1):+.2f} % | {100 * np.std(tr, ddof=1) / b:.2f} % | "
                 f"{100 * (fit(n, range(15)) / fit('k5', range(15)) - 1):+.2f} % |")
    L += ["", "Script: analysis/noise_check_v2.py."]
L += ["", "## S9. Heuristic interface (moved from the paper)", "",
      "The heuristic receives one value per candidate (except energy_left_frac, one value per decision) and returns one positive score per candidate.", "",
      "| Input | Meaning | Template |", "|---|---|---|",
      "| dist_m | distance from current position to candidate start (m) | T1-T3 |",
      "| turn_deg | turning needed to align with the candidate (deg) | T2, T3 |",
      "| swath_len_m | candidate swath length (m) | T2, T3 |",
      "| energy_left_frac | usable battery left in the sortie (scalar, 0-1) | T3 |",
      "| depot_dist_m | distance from candidate end to depot (m) | T3 |",
      "| fits | 1 if travel + swath + return fits the battery, else 0 | T3 |",
      "", "Inputs hidden by a template are replaced by constants during evolution and testing."]
open(os.path.join(OUT, "supplement.md"), "w").write("\n".join(L) + "\n")

# Figure S1
sel3 = "B2_k5"; R = []
for t in ["testA", "testB", "testC"]:
    r = pd.concat([pd.read_csv(os.path.join(EVAL, f"{t}_{s}", "runs.csv")) for s in ("v3", "beta", "k_ext")]); r["set"] = t; R.append(r)
R = pd.concat(R); R = R[R.budget == "3x3"]; R["key"] = R.set + "/" + R.field_id
d = R.groupby(["key", "method"]).energy_MJ.mean().unstack(); sw = R.groupby("key").n_swaths.first()
plt.rcParams.update({"font.family": "serif", "font.serif": ["DejaVu Serif"], "font.size": 8})
fig, axs = plt.subplots(1, 2, figsize=(6.4, 2.6), constrained_layout=True, sharey=False)
cols = {"testA": ("#2a78d6", "o", "Test-A"), "testB": ("#eb6834", "s", "Test-B"), "testC": ("#1baf7a", "^", "Test-C")}
for ax, ref, title in [(axs[0], "B2_distance", "vs B2 (full-budget β)"), (axs[1], sel3, "vs budget-tuned B2* (k = 5)")]:
    g = (d.coder7b / d[ref] - 1) * 100
    for t, (c, mk, lab) in cols.items():
        idx = [k for k in g.index if k.startswith(t)]
        ax.scatter(sw.loc[idx], g.loc[idx], s=12, color=c, marker=mk, label=lab, edgecolor="white", linewidth=0.3)
    ax.axhline(0, color="#7a7974", lw=0.7, ls="--"); ax.set_xscale("log"); ax.set_title(title, fontsize=8)
    ax.set_xlabel("Number of swaths"); ax.grid(color="#e4e3df", lw=0.5); ax.set_axisbelow(True)
    for sp in ("top", "right"): ax.spines[sp].set_visible(False)
axs[0].set_ylabel("Energy change at 3×3 (%)"); axs[0].legend(frameon=False, fontsize=7)
fig.savefig(os.path.join(OUT, "fig_s1_error_analysis.png"), dpi=300)
print("supplement written to", OUT)
