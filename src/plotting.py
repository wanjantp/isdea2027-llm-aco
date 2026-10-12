"""Figures: field + swaths + route, coloured by sortie."""
from __future__ import annotations
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from energy import Costs, RouteResult

SORTIE_COLORS = ["#378ADD", "#D85A30", "#639922", "#7F77DD", "#BA7517", "#D4537E", "#1D9E75", "#888780"]


def plot_route(ax, poly, C: Costs, res: RouteResult, title: str = ""):
    x, y = poly.exterior.xy
    ax.fill(x, y, color="#EAF3DE", ec="#3B6D11", lw=1, zorder=0)
    for ring in poly.interiors:
        hx, hy = ring.xy
        ax.fill(hx, hy, color="white", ec="#3B6D11", lw=1, zorder=1)
    for s in C.sw:
        ax.plot([s.p0[0], s.p1[0]], [s.p0[1], s.p1[1]], color="#C0DD97", lw=0.6, zorder=1)
    for k, sortie in enumerate(res.sorties):
        col = SORTIE_COLORS[k % len(SORTIE_COLORS)]
        pts = [C.depot]
        for (i, d) in sortie:
            pts += [C.start(i, d), C.end(i, d)]
        pts.append(C.depot)
        xs, ys = zip(*pts)
        ax.plot(xs, ys, color=col, lw=1.1, zorder=2, label=f"sortie {k+1}")
    ax.plot(*C.depot, marker="s", color="black", ms=6, zorder=3)
    ax.set_aspect("equal"); ax.set_title(title, fontsize=9); ax.tick_params(labelsize=7)
    ax.legend(fontsize=6, loc="upper right")


def compare_figure(poly, C, results: dict[str, RouteResult], path: str, field_id: str = ""):
    n = len(results)
    fig, axes = plt.subplots(1, n, figsize=(4.2 * n, 4.2))
    if n == 1: axes = [axes]
    for ax, (name, r) in zip(axes, results.items()):
        plot_route(ax, poly, C, r, f"{name}\nE={r.energy_J/1e6:.2f} MJ, T={r.time_s/60:.0f} min, sorties={r.n_sorties}")
    fig.suptitle(field_id, fontsize=11)
    fig.tight_layout(); fig.savefig(path, dpi=130); plt.close(fig)
