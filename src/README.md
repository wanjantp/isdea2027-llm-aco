# src

| module | purpose |
|---|---|
| fields.py | load GeoJSON fields (metres), generate synthetic fields, save |
| swaths.py | parallel swath generation, best sweep angle |
| energy.py | UAVModel (parameters), Costs (precomputed costs), evaluate_route (greedy battery sorties) |
| heuristics.py | baseline heuristics B2-B4, LLM templates T1/T2/T3, loader for LLM code |
| aco.py | MAX-MIN Ant System with pluggable heuristic; boustrophedon baseline B1 |
| plotting.py | route figures |

Run from project root:
    pip install -r requirements.txt
    python experiments/run_baselines.py --fields data/thai_fields/thai_fields_utm48n_local.geojson --out experiments/results/smoke_thai.csv --fig figures/example.png

Depot is the bbox corner (0,0) of each field for every method. Swath width default 5 m.
Heuristic interface (the only thing methods differ in): see heuristics.py docstring.
