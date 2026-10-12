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
