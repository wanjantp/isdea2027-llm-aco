# Plan (5.5 weeks)
- W1 12-18 Oct: literature, problem + energy model, data, ACO + baselines B1-B5
- W2 19-25 Oct: ReEvo integration, local LLM, small test runs
- W3 26 Oct-1 Nov: full evolution 2 LLM x 5 seeds (template T3), then ablation T1/T2
- W4 2-8 Nov: Test-A/B/C, statistics, sensitivity, figures
- W5 9-15 Nov: write 12-page paper
- W6 16-20 Nov: proofread, submit

# Status
- [x] Test-C Thai fields dataset (data/thai_fields)
- [x] Fields2Benchmark downloaded (350 fields, split.json locked)
- [x] synthetic generator (src/fields.py; data/synthetic)
- [x] energy model v0 (src/energy.py) - TODO calibrate parameters, cite airframe
- [x] ACO (MMAS) + baselines B1-B4 (src/aco.py, src/heuristics.py); smoke test OK
- [ ] B5 OR-Tools baseline
- [ ] tune alpha/beta/rho + w_turn on validation set, then lock
- [x] ReEvo-style evolution loop (src/llm_evolve.py, src/llm_client.py); mock test OK
- [ ] run real evolution on chopin (local T3 seed 0) and inspect
- [ ] local LLM setup on chopin: bash setup_chopin.sh (conda env isdea + Ollama)

# LLM roster (decided 2026-10-12)
- local main P1: qwen3.5:9b (latest small, think=false); anchor: qwen2.5-coder:7b (seed0 running); optional: qwen3.5:35b-a3b-coding
- API main P2: openai/gpt-6-luna via OpenRouter; alt: anthropic/claude-haiku-5.5; parity: qwen/qwen3.5-9b; top ref: openai/gpt-6-sol (1 seed)
- repair_attempts config added (default 0); think disabled for all models

# Locked parameters (2026-10-13, tuned on validation split, 25 fields x 3 seeds, experiments/results/tune)
- ACO: alpha=1.0, beta=3.0, rho=0.1 (best of 27-point grid; 0.9662 ratio to B1)
- B3 w_turn: optimum 0.0 (=B2); kept 0.05 as best non-zero (0.9671). Trend: 0.05->0.9671, 0.1->0.9688, 0.25->0.9723, 0.5->0.9788, 1.0->0.9900
- B4 (w_turn, w_depot): optimum (0,0); kept (0.05, 0.25) = 0.9678
- Interpretation: linear hand-crafted terms (turn, depot) add nothing over distance-only ACO; adjacent swaths always need ~180 deg turns so turn_deg does not discriminate.
