# What Do LLM-Evolved Heuristics Add Beyond Tuning?

Code, data and results for *"What Do LLM-Evolved Heuristics Add Beyond Tuning? Ant Colony
Optimisation for Energy-Efficient Agricultural UAV Coverage at Low Compute Budgets"*
(P. Wanjantuk, submitted to ISDEA 2027). The manuscript itself is not part of this repository.

Twenty-seven ACO heuristics were evolved with a ReEvo-style loop and nine LLM configurations,
then compared on 128 test fields with distance-only ACO (B2) and a budget-tuned control (B2*).

## Contents

| Path | What it holds |
|---|---|
| `src/` | field loader, swath generator, energy model, MAX-MIN Ant System, baselines B1-B4, LLM evolution loop (see `src/README.md`) |
| `data/thai_fields/` | Test-C: 20 Thai fields from OpenStreetMap (Khon Kaen), ODbL 1.0 |
| `data/fields2benchmark/` | Fields2Benchmark polygons (CC BY 4.0) and the fixed split (`split.json`) into validation / Test-A / Test-B / pool |
| `data/train/`, `data/synthetic/` | the 30 training fields (20 from the pool, 10 synthetic) |
| `data/energy/` | UAV parameters (DJI Agras T25) and the U-turn-cost sensitivity variants |
| `experiments/configs/` | one config per LLM configuration (model, template T1/T2/T3, repair) |
| `experiments/controls/` | B2* exponent variants and turn-factor knock-out programs |
| `experiments/results/evolve/` | all 27 evolution runs: every program with its status and fitness (`heuristics.jsonl`, 16 200 programs), `state.json`, `best_heuristic.py`, run logs |
| `experiments/results/eval/` | validation and test evaluations (`runs.csv` per planner, field, budget and seed) |
| `analysis/` | statistics (`analysis.py` -> `numbers.json`), paper figures (`make_figs.py`), supplement generator, fitness-noise check |
| `supplement/` | Supplement S1-S9 (`supplement.md`) |
| `MODELS.md` | exact model identifiers, prices and access dates |

## Reproduce

```bash
conda env create -f environment.yml   # or: pip install -r requirements.txt
# 1. evolve one heuristic (local model via Ollama; OpenRouter configs need LLM_API_KEY)
python src/llm_evolve.py --config experiments/configs/evolve_local_qwen25coder7b_T3.json --seed 0 \
       --out experiments/results/evolve/local_qwen25coder7b_T3_v3_s0
# 2. evaluate the selected heuristics and baselines on the test sets
bash run_test_v3.sh
# 3. statistics, figures and supplement from the stored results
python analysis/analysis.py
python analysis/make_figs.py
python analysis/supplement.py
```

Steps 3 only need the stored CSV results, so the paper's numbers can be checked without any LLM.
The API key is never stored in the repository; set `LLM_API_KEY` in the environment.

## Licence

Code: MIT (see `LICENSE`). Data keep their own licences: Thai fields © OpenStreetMap contributors (ODbL 1.0);
Fields2Benchmark (CC BY 4.0, Mier et al., Zenodo, https://doi.org/10.5281/zenodo.14524735).
