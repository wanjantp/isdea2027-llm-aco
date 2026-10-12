# Evolution configs

Naming: evolve_<where>_<model>_<template>[_repair].json
- local = Ollama on chopin, or = OpenRouter (export LLM_API_KEY=sk-or-...), T1/T2/T3 = heuristic template (ablation), repair = one self-repair round.
- think=false everywhere: all models compared in plain generation mode. Prices (USD/1M tokens) as listed on OpenRouter 2026-10-12; update if changed.
- Model IDs for OpenAI on OpenRouter were inferred from display names; verify on openrouter.ai before running.

| config | model | role |
|---|---|---|
| evolve_local_qwen25coder7b_T3 | qwen2.5-coder:7b | local, literature anchor (same family as Zhang et al. 2024 / CALM) |
| evolve_local_qwen35_9b_T3 | qwen3.5:9b | local, MAIN small model (P1) |
| evolve_local_qwen35_9b_T1 / _T2 | qwen3.5:9b | ablation: distance-only / geometry-only templates |
| evolve_local_qwen35_9b_T3_repair | qwen3.5:9b | cheap fix: one self-repair round for failed code |
| evolve_local_qwen35_35b_coding_T3 | qwen3.5:35b-a3b-coding-nvfp4 | optional larger local model (22 GB VRAM) |
| evolve_or_gpt6luna_T3 | openai/gpt-6-luna | MAIN cheap API model (P2) |
| evolve_or_haiku55_T3 | anthropic/claude-haiku-5.5 | alternative cheap API model |
| evolve_or_qwen35_9b_T3 | qwen/qwen3.5-9b | same model as local via API: parity check |
| evolve_or_gpt6sol_T3 | openai/gpt-6-sol | top-tier reference, 1 seed only |
| evolve_local_T3 | qwen2.5-coder:7b | (original config used for the first run, kept for reproducibility) |
| evolve_smoke_mock | mock | plumbing test, no model |

Run:  python src/llm_evolve.py --config experiments/configs/<name>.json --seed <s> --out experiments/results/evolve/<name>_s<s>
