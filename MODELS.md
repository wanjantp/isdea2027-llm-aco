# LLMs used for evolution (all runs October 2026, temperature 0.8, reasoning/thinking mode off, one prompt set for all models)

| Configuration | Provider / endpoint | Model ID | Price in / out (USD per 1M tokens, Oct 2026) | Runs (seeds) |
|---|---|---|---|---|
| qwen2.5-coder:7b T3 | Ollama (local, NVIDIA A100, chopin) | `qwen2.5-coder:7b` | - | 3 (s0-s2) |
| qwen3.5:9b T1 / T2 / T3 / T3+repair | Ollama (local, NVIDIA A100, chopin) | `qwen3.5:9b` | - | 3 / 3 / 5 / 3 |
| gpt-6-luna T3 | OpenRouter | `openai/gpt-6-luna` | 0.10 / 0.50 | 5 (s0-s4) |
| claude-haiku-5.5 T3 | OpenRouter | `anthropic/claude-haiku-5.5` | 0.10 / 0.50 | 3 (s0-s2) |
| gpt-6-sol T3 | OpenRouter | `openai/gpt-6-sol` | 2.00 / 10.00 | 1 (s0) |
| qwen3.5-9b T3 (parity) | OpenRouter | `qwen/qwen3.5-9b` | 0.08 / 0.13 | 1 (s0) |

Local models are the default Ollama builds of these tags (quantised). Record the exact digests for reproducibility
(run on chopin: `ollama list` and `ollama show qwen3.5:9b --modelfile | head`), e.g.:

- qwen2.5-coder:7b  digest: [[fill from `ollama list`]]
- qwen3.5:9b        digest: [[fill from `ollama list`]]

The 17 local runs took 16.5 h wall-clock in total on one A100 (sum of elapsed_s in state.json).
API models may be updated behind the same ID; every generated program and log is in experiments/results/evolve/.
