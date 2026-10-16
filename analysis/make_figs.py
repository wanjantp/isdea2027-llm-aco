"""Rebuild the paper figures. Run from the repo root:  python analysis/make_figs.py
Fig. 1: method schematic. Fig. 2: energy vs ACO budget for B2, budget-tuned B2*, two evolved heuristics on Test-A/B/C."""
import os, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
HERE = os.path.dirname(os.path.abspath(__file__)); EVAL = os.path.join(HERE, "..", "experiments", "results", "eval")
os.makedirs(os.path.join(HERE, "fig"), exist_ok=True)
plt.rcParams["svg.fonttype"] = "path"  # text as outlines so the SVG renders identically everywhere
plt.rcParams.update({"font.family": "serif", "font.serif": ["DejaVu Serif"], "axes.linewidth": 0.6, "xtick.major.width": 0.5,
                     "ytick.major.width": 0.5, "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e"})
BUD = ["1x1", "3x3", "5x10", "15x40", "30x150"]
SEL = {"1x1": "B2_k8", "3x3": "B2_k5", "5x10": "B2_k2", "15x40": "B2_distance", "30x150": "B2_distance"}  # k chosen on validation

def curves():
    rows = []
    for t in ["testA", "testB", "testC"]:
        r = pd.concat([pd.read_csv(f"{EVAL}/{t}_{s}/runs.csv") for s in ("v3", "beta", "k_ext")])
        b1 = r[r.method == "B1_boustrophedon"].groupby("field_id").energy_MJ.mean()
        r = r[r.budget.isin(BUD)].copy(); r["rB1"] = r.energy_MJ / r.field_id.map(b1)
        c = r.groupby(["method", "budget"]).rB1.mean()
        for b in BUD:
            for m in ["B2_distance", "coder7b", "sol"]: rows.append((t, m, b, c[(m, b)]))
            ev = [c[(m, b)] for m in ["coder7b", "q9b_T3rep", "q9b_T3", "q9b_T2", "q9b_T1", "q9b_api", "haiku", "luna", "sol"]]
            rows.append((t, "ev_min", b, min(ev))); rows.append((t, "ev_max", b, max(ev)))
            rows.append((t, "B2star", b, c[(SEL[b], b)]))
    return pd.DataFrame(rows, columns=["set", "method", "budget", "rB1"])

def fig2(c):
    series = [("B2_distance", "B2 (full-budget β)", "#7a7974", "--", "o"), ("B2star", "B2* (β tuned per budget)", "#2a78d6", "-", "s"),
              ("coder7b", "qwen2.5-coder:7b (local)", "#eb6834", "-", "^"), ("sol", "gpt-6-sol (API)", "#1baf7a", ":", "D")]
    names = {"testA": "Test-A (100 fields)", "testB": "Test-B (8 large fields)", "testC": "Test-C (20 Thai fields)"}
    fig, axs = plt.subplots(1, 3, figsize=(4.8, 2.0), constrained_layout=True)
    for ax, s in zip(axs, names):
        lo = c[(c.set == s) & (c.method == "ev_min")].copy(); hi = c[(c.set == s) & (c.method == "ev_max")].copy()
        for d in (lo, hi): d["x"] = d.budget.map({b: i for i, b in enumerate(BUD)})
        lo, hi = lo.sort_values("x"), hi.sort_values("x")
        ax.fill_between(lo.x, lo.rB1.values, hi.rB1.values, color="#eb6834", alpha=0.13, lw=0, label="Range of nine evolved", zorder=1)
        for m, lab, col, ls, mk in series:
            d = c[(c.set == s) & (c.method == m)].copy(); d["x"] = d.budget.map({b: i for i, b in enumerate(BUD)}); d = d.sort_values("x")
            ax.plot(d.x, d.rB1, ls=ls, color=col, lw=1.2, marker=mk, ms=3.2, mec="white", mew=0.4, label=lab, zorder=3)
        ax.set_xticks(range(5)); ax.set_xticklabels(["1", "9", "50", "600", "4.5k"], fontsize=7.2); ax.set_xlim(-0.3, 4.3)
        ax.set_title(names[s], fontsize=7.6, color="#0b0b0b"); ax.grid(axis="y", color="#e4e3df", lw=0.5); ax.set_axisbelow(True)
        for sp in ("top", "right"): ax.spines[sp].set_visible(False)
        ax.tick_params(labelsize=7.2)
    axs[0].set_ylabel("Energy / boustrophedon", fontsize=7.4)
    fig.supxlabel("Ant constructions per run (1×1, 3×3, 5×10, 15×40, 30×150)", fontsize=7.4)
    h, l = axs[0].get_legend_handles_labels(); fig.legend(h, l, loc="outside upper center", ncol=3, frameon=False, fontsize=7.2, columnspacing=1.0, handlelength=1.8)
    fig.savefig(os.path.join(HERE, "fig", "fig2_energy_compute.png"), dpi=600)
    fig.savefig(os.path.join(HERE, "fig", "fig2_energy_compute.svg"))  # vector copy embedded in Word (svgBlip)

def fig1():
    fig, ax = plt.subplots(figsize=(4.8, 2.08)); ax.set_xlim(0, 100); ax.set_ylim(0, 34); ax.axis("off")
    ink, sub, acc, acc2, fs = "#0b0b0b", "#52514e", "#2a78d6", "#eb6834", 7.0
    def box(x, y, w, h, t, ec=sub, bold=False):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.2", ec=ec, fc="white", lw=0.7))
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", color=ink, fontsize=fs, fontweight="bold" if bold else "normal", linespacing=1.15)
    def arr(p, q, col=sub): ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=6, lw=0.7, color=col, shrinkA=0, shrinkB=0))
    for x, w in ((0.5, 59.5), (64, 35.5)):
        ax.add_patch(FancyBboxPatch((x, 0.5), w, 33, boxstyle="round,pad=0,rounding_size=1.5", ec="#c9c8c2", fc="#f6f5f2", lw=0.6))
    ax.text(2, 30.8, "Offline, once: evolve η", fontsize=7.6, fontweight="bold", color=ink, va="center")
    ax.text(65.5, 30.8, "Online, per mission", fontsize=7.6, fontweight="bold", color=ink, va="center")
    box(2, 16, 17, 11.5, "Task,\ninterface,\ninitial η"); box(21.5, 16, 17, 11.5, "LLM\nlocal 7–9B\nor API", ec=acc, bold=True)
    box(41, 16, 17.5, 11.5, "Candidate η\n(Python),\nsandbox test")
    box(21.5, 2.5, 17, 11, "Reflections;\nkeep the\n12 best"); box(41, 2.5, 17.5, 11, "Fitness:\nE/E(B1) of\nACO 3×3 on\n30 fields")
    arr((19, 21.75), (21.5, 21.75)); arr((38.5, 21.75), (41, 21.75)); arr((49.75, 16), (49.75, 13.5)); arr((41, 8), (38.5, 8)); arr((30, 13.5), (30, 16))
    ax.text(10.5, 8, "×50\ngenerations", fontsize=6.8, color=sub, ha="center", va="center", linespacing=1.15)
    box(65.5, 16, 15.5, 11.5, "Evolved η\n(few lines\nof numpy)", ec=acc2, bold=True); box(83, 16, 15, 11.5, "Field\npolygon\n→ swaths")
    box(65.5, 2.5, 32.5, 11, "ACO, 1×1 to 5×10\n→ swath order,\ndirections, sorties", ec=acc2)
    arr((73.25, 16), (73.25, 13.5)); arr((90.5, 16), (90.5, 13.5)); arr((58.5, 21.75), (65.5, 21.75), col=acc2)
    ax.text(62.0, 23.0, "best", fontsize=6.8, color=acc2, ha="center", va="bottom")
    fig.savefig(os.path.join(HERE, "fig", "fig1_method.png"), dpi=600, bbox_inches="tight", pad_inches=0.02)
    fig.savefig(os.path.join(HERE, "fig", "fig1_method.svg"), bbox_inches="tight", pad_inches=0.02)

if __name__ == "__main__":
    fig1(); fig2(curves()); print("figures written to analysis/fig/")
