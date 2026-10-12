"""ReEvo-style evolution of the ACO heuristic function with an LLM.

    python src/llm_evolve.py --config experiments/configs/evolve_local.json --seed 0 --out experiments/results/evolve/local_s0

Loop (per Ye et al. 2024, simplified):
  init population  -> LLM writes N heuristics from the task description + template (+ seed heuristic)
  repeat until budget:
     select pairs (better, worse) -> short-term reflection (why better?) -> crossover child
     long-term reflection (accumulated insights) -> elitist mutation child
     evaluate children in sandboxed subprocesses (timeout), keep top-N (population)
Fitness = mean over training fields of  E(heuristic) / E(boustrophedon)   (lower is better).
Every generated program is logged with status: ok | syntax | runtime | invalid_output | timeout.
"""
from __future__ import annotations
import argparse, json, os, sys, time, random, traceback, multiprocessing as mp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm_client import LLMClient, extract_code
from heuristics import TEMPLATE_T1_DIST, TEMPLATE_T2_GEOM, TEMPLATE_T3_FULL, mask_for_template

TEMPLATES = {"T1": TEMPLATE_T1_DIST, "T2": TEMPLATE_T2_GEOM, "T3": TEMPLATE_T3_FULL}

# ------------------------------------------------------------------------------------ prompts
SYSTEM = "You are an expert in combinatorial optimisation, ant colony optimisation and agricultural robotics. You write concise, correct, vectorised numpy code."

TASK = """Problem: an agricultural spraying UAV must fly every swath (parallel strip) of a field exactly once. Swaths can be flown in either direction.
The UAV starts at a depot, has a limited battery per sortie, and must return to the depot to swap batteries. Total cost = energy for
flying swaths + transit between swaths + turning (proportional to turn angle) + a fixed overhead per sortie. We minimise total energy.

A MAX-MIN Ant System builds the swath order step by step. At each step the ant is at the end of the previous swath and chooses the next
(swath, direction) with probability proportional to pheromone^alpha * heuristic^beta. YOUR JOB is to design the heuristic function
`heuristic(...)` that scores every candidate (higher = more desirable). All inputs are numpy arrays of equal length K (one entry per
candidate), except energy_left_frac which is a scalar.

{features}

Requirements: return a numpy array of K strictly positive finite floats; use only numpy; no loops over K if avoidable; no printing;
no randomness; keep it under 40 lines. Respond with a one-sentence description in curly braces {{like this}} followed by ONE python code block."""

FEATURES = {
    "T3": """Inputs:
- dist_m: distance from the current position to the candidate's start point (m)
- turn_deg: total turning required to leave the current heading and align with the candidate (deg, 0-360)
- swath_len_m: length of the candidate swath (m)
- energy_left_frac: fraction of usable battery left in the current sortie (scalar, 0-1)
- depot_dist_m: distance from the candidate's END point back to the depot (m)
- fits: 1.0 if (travel + fly + return to depot) fits in the remaining battery, else 0.0
Hints: a candidate that does not fit forces a battery swap (costly); when the battery is nearly empty it may be wise to pick swaths that end
near the depot; sharp turns are expensive; adjacent parallel swaths need small distance and ~180 degree turns.""",
    "T2": """Inputs:
- dist_m: distance from the current position to the candidate's start point (m)
- turn_deg: total turning required to leave the current heading and align with the candidate (deg, 0-360)
- swath_len_m: length of the candidate swath (m)
- energy_left_frac, depot_dist_m, fits: constant placeholders in this variant, carry no information (ignore them)
Hints: sharp turns are expensive; adjacent parallel swaths need small distance and ~180 degree turns.""",
    "T1": """Inputs:
- dist_m: distance from the current position to the candidate's start point (m)
- turn_deg, swath_len_m, energy_left_frac, depot_dist_m, fits: constant placeholders in this variant, carry no information (ignore them)""",
}

P_INIT = """{task}

Here is a trivial reference heuristic (distance only):
```python
{seed}
```
Design a NEW and better heuristic. Be creative but keep the exact function signature."""

P_SHORT_REFLECT = """{task}

Below are two heuristics. The first performs BETTER (fitness {f_better:.4f}, lower is better) than the second (fitness {f_worse:.4f}).
[Better]
```python
{better}
```
[Worse]
```python
{worse}
```
In 2-4 sentences, state the design ideas that make the first better and what to avoid. Output only the reflection, no code."""

P_CROSSOVER = """{task}

[Better heuristic, fitness {f_better:.4f}]
```python
{better}
```
[Worse heuristic, fitness {f_worse:.4f}]
```python
{worse}
```
[Reflection]
{reflection}

Write an improved heuristic that combines the strengths of both following the reflection."""

P_LONG_REFLECT = """You are tracking insights while evolving a heuristic for the task below.
{task}

[Previous long-term insights]
{prior}
[New short-term reflections]
{new}

Merge them into an updated list of at most 6 concise, general design insights (bullet points). Output only the list."""

P_MUTATE = """{task}

[Current best heuristic, fitness {f_best:.4f} (lower is better)]
```python
{best}
```
[Accumulated design insights]
{insights}

Write a NEW heuristic that improves on the best one by applying the insights. Change at least one substantive idea, not only constants."""


# ------------------------------------------------------------------------------------ evaluation (subprocess)
P_REPAIR = """{task}

The following heuristic failed when executed. Status: {status}. Error: {error}
```python
{code}
```
Fix the problem and return the corrected heuristic (same signature; output must be K strictly positive finite floats; guard divisions
and powers against zero/negative values with np.maximum, np.clip or small epsilons). Keep the same design idea."""


def _single_thread():
    """numpy/BLAS must not spawn one thread per core inside every worker, or N workers oversubscribe the CPU."""
    for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[k] = "1"


def swath_cache(fields_path: str, field_ids: list, width: float, cache_path: str):
    """Swaths for the training fields, generated once and pickled (saves ~10 % of every evaluation)."""
    import pickle
    if os.path.exists(cache_path):
        return pickle.load(open(cache_path, "rb"))
    from fields import load_fields
    from swaths import generate_swaths, best_angle
    out = {f.id: generate_swaths(f.polygon, width, best_angle(f.polygon, width)) for f in load_fields(fields_path, field_ids)}
    pickle.dump(out, open(cache_path, "wb"))
    return out


def _eval_worker(code: str, fields_path: str, field_ids: list, template: str, aco_cfg: dict, width: float, ref: dict, cache_path: str, q):
    try:
        _single_thread()
        import warnings; warnings.filterwarnings("ignore")
        import numpy as np; np.seterr(all="ignore")
        from energy import Costs, UAVModel
        from aco import ACO, ACOParams
        from heuristics import load_heuristic_from_code
        try:
            fn = load_heuristic_from_code(code)
        except SyntaxError as e:
            q.put({"status": "syntax", "error": str(e)}); return
        except Exception as e:
            q.put({"status": "invalid_output" if "invalid output" in str(e) else "runtime", "error": str(e)[:300]}); return
        uav = UAVModel.load(aco_cfg["uav"]) if aco_cfg.get("uav") else UAVModel()
        params = ACOParams(n_ants=aco_cfg["n_ants"], n_iters=aco_cfg["n_iters"])
        swaths = swath_cache(fields_path, field_ids, width, cache_path)
        ratios, t_fields = [], []
        for fid in field_ids:
            t0 = time.time()
            C = Costs(swaths[fid], (0.0, 0.0), uav)
            _, r, _ = ACO(params, fn, seed=aco_cfg.get("seed", 0), feature_mask=mask_for_template(template)).run(C)
            ratios.append(r.energy_J / ref[fid]); t_fields.append(time.time() - t0)
        q.put({"status": "ok", "fitness": float(np.mean(ratios)), "per_field": ratios, "aco_s": round(sum(t_fields), 1)})
    except Exception as e:
        q.put({"status": "runtime", "error": (str(e) or type(e).__name__)[:300]})


def evaluate(code, fields_path, field_ids, template, aco_cfg, width, ref, timeout_s, cache_path):
    q = mp.Queue()
    p = mp.Process(target=_eval_worker, args=(code, fields_path, field_ids, template, aco_cfg, width, ref, cache_path, q))
    t0 = time.time(); p.start(); p.join(timeout_s)
    if p.is_alive():
        p.terminate(); p.join()
        return {"status": "timeout", "error": f">{timeout_s}s", "eval_s": time.time() - t0}
    try:
        out = q.get(timeout=5)
    except Exception:
        out = {"status": "runtime", "error": "worker died"}
    out["eval_s"] = time.time() - t0
    return out


def reference_energies(fields_path, field_ids, width, uav_path):
    from fields import load_fields
    from swaths import generate_swaths, best_angle
    from energy import Costs, UAVModel
    from aco import boustrophedon
    uav = UAVModel.load(uav_path) if uav_path else UAVModel()
    ref = {}
    for f in load_fields(fields_path, field_ids):
        sw = generate_swaths(f.polygon, width, best_angle(f.polygon, width))
        _, r = boustrophedon(Costs(sw, (0.0, 0.0), uav)); ref[f.id] = r.energy_J
    return ref


# ------------------------------------------------------------------------------------ main loop
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True); ap.add_argument("--seed", type=int, default=0); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    cfg = json.load(open(a.config))
    rng = random.Random(a.seed)
    os.makedirs(a.out, exist_ok=True)
    llm = LLMClient.from_config(cfg["llm"], log_path=os.path.join(a.out, "llm_calls.jsonl"))
    template = cfg.get("template", "T3")
    task = TASK.format(features=FEATURES[template])
    seed_code = TEMPLATES[template].strip()
    fields_path, width = cfg["train_fields"], cfg.get("swath_width", 5.0)
    train_ids = cfg.get("train_ids") or [f["properties"]["field_id"] for f in json.load(open(fields_path))["features"]]
    aco_cfg = cfg["aco_eval"]; timeout_s = cfg.get("eval_timeout_s", 600)
    cache_path = os.path.join(a.out, "swath_cache.pkl")
    swath_cache(fields_path, train_ids, width, cache_path)
    ref = reference_energies(fields_path, train_ids, width, aco_cfg.get("uav"))
    budget, pop_size = cfg.get("budget", 300), cfg.get("pop_size", 10)
    n_workers = cfg.get("n_workers", 4)
    log_f = open(os.path.join(a.out, "heuristics.jsonl"), "a", encoding="utf-8")
    archive = []        # all evaluated: dict(code, status, fitness, gen, op, desc)
    pop = []            # valid ones, sorted by fitness
    insights = "(none yet)"
    n_generated = 0
    t_start = time.time()

    def ask(prompt, temperature=None):
        text, u = llm.chat(SYSTEM, prompt, temperature)
        return text

    def gen_and_eval(prompt, gen, op):
        nonlocal n_generated
        text = ask(prompt)
        code = extract_code(text)
        import re
        m = re.search(r"\{(.+?)\}", text, re.S); desc = m.group(1).strip() if m else ""
        n_generated += 1
        return {"code": code, "desc": desc, "gen": gen, "op": op, "idx": n_generated, "raw": text}

    repair_attempts = cfg.get("repair_attempts", 0)   # 0 = off (default); 1 = one self-repair round for failed code

    def eval_batch(items, _depth=0):
        # evaluate several candidates concurrently (each in its own subprocess)
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=n_workers) as ex:
            outs = list(ex.map(lambda it: evaluate(it["code"], fields_path, train_ids, template, aco_cfg, width, ref, timeout_s, cache_path), items))
        failed = []
        for it, o in zip(items, outs):
            it.update(o); archive.append(it)
            log_f.write(json.dumps({k: v for k, v in it.items() if k != "raw"}) + "\n"); log_f.flush()
            if o["status"] == "ok": pop.append(it)
            elif _depth < repair_attempts and n_generated < budget: failed.append(it)
        pop.sort(key=lambda x: x["fitness"]); del pop[pop_size:]
        if failed:
            repaired = []
            for it in failed:
                if n_generated >= budget: break
                r = gen_and_eval(P_REPAIR.format(task=task, status=it["status"], error=it.get("error", ""), code=it["code"]), it["gen"], "repair")
                r["parent_idx"] = it["idx"]; repaired.append(r)
            if repaired: eval_batch(repaired, _depth + 1)

    # seed heuristic as a known-valid member
    seed_item = {"code": seed_code, "desc": "seed: inverse distance", "gen": 0, "op": "seed", "idx": 0}
    eval_batch([seed_item])
    print(f"seed fitness {seed_item.get('fitness'):.4f}", flush=True)

    # initial population
    gen = 0
    init = [gen_and_eval(P_INIT.format(task=task, seed=seed_code), gen, "init") for _ in range(pop_size)]
    eval_batch(init)
    print(f"gen {gen}: generated {n_generated}, valid {len(pop)}, best {pop[0]['fitness']:.4f}", flush=True)

    while n_generated < budget:
        gen += 1
        children = []
        # crossover with short-term reflection
        n_cross = max(2, pop_size // 2)
        new_reflections = []
        for _ in range(n_cross):
            if len(pop) < 2: break
            p1, p2 = rng.sample(pop, 2)
            better, worse = (p1, p2) if p1["fitness"] <= p2["fitness"] else (p2, p1)
            refl = ask(P_SHORT_REFLECT.format(task=task, better=better["code"], worse=worse["code"], f_better=better["fitness"], f_worse=worse["fitness"]), temperature=0.5)
            new_reflections.append(refl.strip())
            children.append(gen_and_eval(P_CROSSOVER.format(task=task, better=better["code"], worse=worse["code"], f_better=better["fitness"], f_worse=worse["fitness"], reflection=refl), gen, "crossover"))
            if n_generated >= budget: break
        # long-term reflection + elitist mutation
        if new_reflections:
            insights = ask(P_LONG_REFLECT.format(task=task, prior=insights, new="\n---\n".join(new_reflections)), temperature=0.3).strip()
        n_mut = max(1, pop_size - n_cross)
        for _ in range(n_mut):
            if n_generated >= budget: break
            children.append(gen_and_eval(P_MUTATE.format(task=task, best=pop[0]["code"], f_best=pop[0]["fitness"], insights=insights), gen, "mutation"))
        eval_batch(children)
        st = {s: sum(1 for x in archive if x["status"] == s) for s in ("ok", "syntax", "runtime", "invalid_output", "timeout")}
        ev = [x["eval_s"] for x in children if "eval_s" in x]
        print(f"gen {gen}: generated {n_generated}/{budget}, best {pop[0]['fitness']:.4f} (gen {pop[0]['gen']}), status {st}, "
              f"eval {sum(ev)/max(1,len(ev)):.0f}s/heur, "
              f"llm {llm.n_calls} calls {llm.total.completion_tokens} out-tok {llm.total.cost_usd:.3f} USD, {(time.time()-t_start)/60:.1f} min", flush=True)
        json.dump({"insights": insights, "best": pop[0], "population": pop, "llm": llm.summary(), "status_counts": st,
                   "elapsed_s": time.time() - t_start, "n_generated": n_generated, "config": cfg, "seed": a.seed},
                  open(os.path.join(a.out, "state.json"), "w"), indent=1)

    best = pop[0]
    open(os.path.join(a.out, "best_heuristic.py"), "w").write(best["code"] + "\n")
    print(f"DONE best fitness {best['fitness']:.4f}: {best['desc']}\n{best['code']}")


if __name__ == "__main__":
    _single_thread()
    mp.set_start_method("spawn", force=True)
    main()
