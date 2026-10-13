"""Summarise all evolution runs: LLM cost/tokens/time, code-failure breakdown, best fitness, convergence.

  python experiments/summarize_runs.py --runs "experiments/results/evolve/*_v3_s*" --out experiments/results/summary_runs
Outputs: runs_table.csv (one row per run), failure_table.csv (per LLM/config), convergence.csv (best-so-far per generation per run)
"""
import argparse, glob, json, os, csv, re
from collections import Counter, defaultdict

ap = argparse.ArgumentParser()
ap.add_argument("--runs", default="experiments/results/evolve/*_v3_s*")
ap.add_argument("--out", default="experiments/results/summary_runs")
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)

rows, conv, fail = [], [], defaultdict(Counter)
for d in sorted(glob.glob(a.runs)):
    if not os.path.isdir(d) or not os.path.exists(os.path.join(d, "state.json")): continue
    st = json.load(open(os.path.join(d, "state.json")))
    name = os.path.basename(d)
    m = re.match(r"(.+)_s(\d+)$", name); cfg, seed = (m.group(1), int(m.group(2))) if m else (name, -1)
    hs = [json.loads(l) for l in open(os.path.join(d, "heuristics.jsonl"), encoding="utf-8")]
    seed_fit = next((h["fitness"] for h in hs if h.get("op") == "seed"), None)
    llm = st["llm"]; sc = Counter(h["status"] for h in hs if h.get("op") != "seed")
    n = sum(sc.values())
    # repairs
    rep = [h for h in hs if h.get("op") == "repair"]; rep_ok = sum(h["status"] == "ok" for h in rep)
    rows.append(dict(run=name, config=cfg, seed=seed, model=llm["model"], provider=llm["provider"], template=st["config"].get("template"),
                     n_generated=n, ok=sc["ok"], syntax=sc["syntax"], runtime=sc["runtime"], invalid_output=sc["invalid_output"], timeout=sc["timeout"],
                     ok_rate=round(sc["ok"] / max(1, n), 3), repairs=len(rep), repairs_ok=rep_ok,
                     seed_fitness=round(seed_fit, 4) if seed_fit else None, best_fitness=round(st["best"]["fitness"], 4),
                     gain_pct=round(100 * (1 - st["best"]["fitness"] / seed_fit), 2) if seed_fit else None, best_gen=st["best"]["gen"],
                     llm_calls=llm["calls"], prompt_tokens=llm["prompt_tokens"], completion_tokens=llm["completion_tokens"],
                     cost_usd=round(llm["cost_usd"], 4), llm_time_min=round(llm["seconds"] / 60, 1), wall_min=round(st["elapsed_s"] / 60, 1)))
    fail[(llm["model"], st["config"].get("template"))].update(sc)
    # convergence: best-so-far by generation (valid only)
    best = None
    for g in sorted(set(h["gen"] for h in hs)):
        vals = [h["fitness"] for h in hs if h["gen"] <= g and h["status"] == "ok"]
        best = min(vals) if vals else None
        conv.append(dict(run=name, config=cfg, seed=seed, gen=g, best_so_far=best))

def w(path, rs):
    if not rs: return
    with open(path, "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(rs[0].keys())); wr.writeheader(); wr.writerows(rs)
w(os.path.join(a.out, "runs_table.csv"), rows)
w(os.path.join(a.out, "convergence.csv"), conv)
frows = [dict(model=k[0], template=k[1], **{s: c[s] for s in ("ok", "syntax", "runtime", "invalid_output", "timeout")},
              total=sum(c.values()), ok_rate=round(c["ok"] / max(1, sum(c.values())), 3)) for k, c in fail.items()]
w(os.path.join(a.out, "failure_table.csv"), frows)
print(f"{len(rows)} runs")
print(f"{'run':40s} {'ok%':>5s} {'seed':>7s} {'best':>7s} {'gain%':>6s} {'gen':>4s} {'calls':>5s} {'USD':>6s} {'min':>6s}")
for r in rows:
    print(f"{r['run']:40s} {100*r['ok_rate']:5.0f} {r['seed_fitness'] or 0:7.4f} {r['best_fitness']:7.4f} {r['gain_pct'] or 0:6.2f} {r['best_gen']:4d} {r['llm_calls']:5d} {r['cost_usd']:6.3f} {r['wall_min']:6.0f}")
