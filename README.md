# ISDEA 2027 project
LLM-Evolved Ant Colony Heuristics for Energy-Aware Agricultural UAV Coverage Path Planning

Target: ISDEA 2027, Okinawa, 24-26 Apr 2027. Submission deadline 20 Nov 2026 (12 pages, Springer LNEE).

## Folder layout
- data/thai_fields/       Test-C: 20 real Thai fields from OSM (Khon Kaen)
- data/fields2benchmark/  Fields2Benchmark (download from WUR), validation + Test-A
- data/synthetic/         generated training fields for the evolution loop
- data/energy/            UAV energy model coefficients (Rodrigues et al.)
- src/                    code: field loader, swath generator, energy model, ACO, baselines, LLM loop
- experiments/            run configs and results (results/ holds CSV/JSON outputs)
- figures/                paper figures
- paper/                  manuscript (Springer template) and references/
- notes/                  planning notes, literature notes
