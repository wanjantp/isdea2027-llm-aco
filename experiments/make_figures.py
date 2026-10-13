"""Paper figures from run_eval / summarize_runs outputs (matplotlib, print-ready, fixed categorical colours).

  python experiments/make_figures.py budget   --eval experiments/results/eval/testA_sweep --out figures/fig_energy_vs_budget.pdf
  python experiments/make_figures.py box      --eval experiments/results/eval/testA_sweep --budget 3x3 --out figures/fig_box_3x3.pdf
  python experiments/make_figures.py converge --summary experiments/results/summary_runs --out figures/fig_convergence.pdf
  python experiments/make_figures.py failures --summary experiments/results/summary_runs --out figures/fig_failures.pdf
"""
import argparse, csv, os, re
from collections import defaultdict
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# fixed categorical order (validated palette); one method = one colour everywhere in the paper
COLORS = {"B1_boustrophedon": "#888780", "B2_distance": "#2a78d6", "B3_dist_turn": "#6da7ec", "B4_dist_turn_battery": "#1baf7a",
          "P1": "#eb6834", "P2": "#e87ba4", "P1_local": "#eb6834", "P2_api": "#e87ba4"}
FALLBACK = ["#eb6834", "#e87ba4", "#eda100", "#008300", "#2a78d6", "#1baf7a"]
BUDGET_ORDER = ["greedy", "1x1", "3x3", "5x10", "15x40", "30x150"]
BUDGET_EVALS = {"greedy": 0.5, "1x1": 1, "3x3": 9, "5x10": 50, "15x40": 600, "30x150": 4500}   # ant constructions per run

plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
                     "grid.color": "#e6e4dc", "grid.linewidth": 0.5, "legend.frameon": False, "figure.dpi": 150})


def color(m, i):
    for k, v in COLORS.items():
        if m == k or m.startswith(k): return v
    return FALLBACK[i % len(FALLBACK)]


def label(m):
    return {"B1_boustrophedon": "Boustrophedon", "B2_distance": "ACO distance-only (B2)", "B3_dist_turn": "ACO distance+turn (B3)",
            "B4_dist_turn_battery": "ACO hand-crafted battery (B4)"}.get(m, m.replace("_", " "))


def read_runs(d):
    return list(csv.DictReader(open(os.path.join(d, "runs.csv"))))


def fig_budget(a):
    rows = read_runs(a.eval)
    b1 = {r["field_id"]: float(r["energy_MJ"]) for r in rows if r["method"] == "B1_boustrophedon"}
    acc = defaultdict(lambda: defaultdict(list))     # method -> budget -> ratios (per field mean over seeds)
    tmp = defaultdict(lambda: defaultdict(list))
    for r in rows:
        if r["method"] == "B1_boustrophedon": continue
        tmp[(r["method"], r["budget"])][r["field_id"]].append(float(r["energy_MJ"]) / b1[r["field_id"]])
    for (m, b), d in tmp.items():
        acc[m][b] = [np.mean(v) for v in d.values()]
    budgets = [b for b in BUDGET_ORDER if any(b in acc[m] for m in acc)]
    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    for i, m in enumerate(acc):
        x = [BUDGET_EVALS[b] for b in budgets if b in acc[m]]
        y = [100 * np.mean(acc[m][b]) for b in budgets if b in acc[m]]
        e = [100 * np.std(acc[m][b]) / np.sqrt(len(acc[m][b])) for b in budgets if b in acc[m]]
        ax.errorbar(x, y, yerr=e, marker="o", ms=4, lw=1.8, capsize=2, color=color(m, i), label=label(m))
    ax.axhline(100, color="#888780", lw=1, ls="--"); ax.text(x[-1], 100.3, "boustrophedon", ha="right", fontsize=8, color="#888780")
    ax.set_xscale("log"); ax.set_xticks([BUDGET_EVALS[b] for b in budgets]); ax.set_xticklabels(budgets)
    ax.set_xlabel("ACO budget (ants × iterations)"); ax.set_ylabel("Energy, % of boustrophedon (mean over fields)")
    ax.legend(fontsize=7.5, loc="upper right"); fig.tight_layout(); fig.savefig(a.out); print("saved", a.out)


def fig_box(a):
    rows = read_runs(a.eval)
    b1 = {r["field_id"]: float(r["energy_MJ"]) for r in rows if r["method"] == "B1_boustrophedon"}
    tmp = defaultdict(lambda: defaultdict(list))
    for r in rows:
        if r["method"] == "B1_boustrophedon" or r["budget"] != a.budget: continue
        tmp[r["method"]][r["field_id"]].append(float(r["energy_MJ"]) / b1[r["field_id"]])
    methods = list(tmp); data = [[100 * np.mean(v) for v in tmp[m].values()] for m in methods]
    fig, ax = plt.subplots(figsize=(5.2, 3.0))
    bp = ax.boxplot(data, widths=0.55, patch_artist=True, showfliers=True, flierprops=dict(marker=".", ms=3, alpha=0.5))
    for i, (box, m) in enumerate(zip(bp["boxes"], methods)):
        box.set(facecolor=color(m, i), alpha=0.35, edgecolor=color(m, i)); bp["medians"][i].set(color=color(m, i), lw=2)
    ax.axhline(100, color="#888780", lw=1, ls="--")
    ax.set_xticks(range(1, len(methods) + 1)); ax.set_xticklabels([label(m) for m in methods], rotation=15, ha="right", fontsize=8)
    ax.set_ylabel(f"Energy, % of boustrophedon (budget {a.budget})"); fig.tight_layout(); fig.savefig(a.out); print("saved", a.out)


def fig_converge(a):
    rows = list(csv.DictReader(open(os.path.join(a.summary, "convergence.csv"))))
    by = defaultdict(lambda: defaultdict(list))
    for r in rows:
        if r["best_so_far"]: by[r["config"]][int(r["gen"])].append(float(r["best_so_far"]))
    fig, ax = plt.subplots(figsize=(5.2, 3.2))
    for i, (cfg, d) in enumerate(sorted(by.items())):
        g = sorted(d); mean = [np.mean(d[x]) for x in g]; lo = [np.min(d[x]) for x in g]; hi = [np.max(d[x]) for x in g]
        c = FALLBACK[i % len(FALLBACK)]
        ax.plot(g, mean, lw=1.8, color=c, label=f"{cfg} (n={len(d[g[0]])})"); ax.fill_between(g, lo, hi, color=c, alpha=0.15, lw=0)
    ax.set_xlabel("Generation"); ax.set_ylabel("Best fitness so far (energy / boustrophedon)")
    ax.legend(fontsize=7); fig.tight_layout(); fig.savefig(a.out); print("saved", a.out)


def fig_failures(a):
    rows = list(csv.DictReader(open(os.path.join(a.summary, "failure_table.csv"))))
    cats = ["ok", "syntax", "runtime", "invalid_output", "timeout"]
    cc = {"ok": "#1baf7a", "syntax": "#eb6834", "runtime": "#eda100", "invalid_output": "#e87ba4", "timeout": "#888780"}
    labels = [f"{r['model']}\n({r['template']})" for r in rows]
    fig, ax = plt.subplots(figsize=(5.2, 2.6)); left = np.zeros(len(rows))
    for c in cats:
        v = np.array([100 * int(r[c]) / int(r["total"]) for r in rows])
        ax.barh(labels, v, left=left, color=cc[c], label=c.replace("_", " "), height=0.6, edgecolor="white", linewidth=1); left += v
    ax.set_xlabel("Generated programs, %"); ax.set_xlim(0, 100); ax.legend(fontsize=7, ncol=5, loc="upper center", bbox_to_anchor=(0.5, 1.25))
    ax.grid(False); fig.tight_layout(); fig.savefig(a.out); print("saved", a.out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["budget", "box", "converge", "failures"])
    ap.add_argument("--eval"); ap.add_argument("--summary"); ap.add_argument("--budget", default="3x3"); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    {"budget": fig_budget, "box": fig_box, "converge": fig_converge, "failures": fig_failures}[a.kind](a)
