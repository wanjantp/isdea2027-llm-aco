#!/usr/bin/env bash
# One-time setup on the GPU server (chopin). Run from ~/ISDEA:   bash setup_chopin.sh
set -e
cd "$(dirname "$0")"

echo "== 1. conda env 'isdea'"
if conda env list | grep -q "^isdea "; then
  conda env update -n isdea -f environment.yml --prune
else
  conda env create -f environment.yml
fi
eval "$(conda shell.bash hook)"; conda activate isdea
python -c "import shapely, numpy, pyproj, matplotlib, scipy; print('python libs ok')"

echo "== 2. smoke test (CPU only)"
python experiments/run_baselines.py --fields data/thai_fields/thai_fields_utm48n_local.geojson \
    --out experiments/results/smoke_chopin.csv --limit 3 --ants 10 --iters 20

echo "== 3. Ollama (local LLM server, no sudo needed)"
mkdir -p ~/bin ~/ollama_models
if ! command -v ollama >/dev/null && [ ! -x ~/bin/ollama ]; then
  curl -L https://ollama.com/download/ollama-linux-amd64.tgz -o /tmp/ollama.tgz
  tar -xzf /tmp/ollama.tgz -C ~/bin --strip-components=1 2>/dev/null || tar -xzf /tmp/ollama.tgz -C ~/bin
fi
export PATH=~/bin:$PATH
grep -q OLLAMA_MODELS ~/.bashrc || cat >> ~/.bashrc <<'EOB'
export PATH=~/bin:$PATH
export OLLAMA_MODELS=~/ollama_models
export OLLAMA_MAX_LOADED_MODELS=1
EOB
export OLLAMA_MODELS=~/ollama_models OLLAMA_MAX_LOADED_MODELS=1
if ! curl -s localhost:11434 >/dev/null; then nohup ollama serve > ~/ollama.log 2>&1 & sleep 5; fi
ollama pull qwen2.5-coder:7b
ollama list

echo "== 4. LLM round trip"
curl -s localhost:11434/api/chat -d '{"model":"qwen2.5-coder:7b","stream":false,"messages":[{"role":"user","content":"Reply with the single word OK"}]}' | python -c "import sys,json; print('LLM says:', json.load(sys.stdin)['message']['content'])"

echo "== 5. evolution loop plumbing test (mock LLM, ~1 min)"
python src/llm_evolve.py --config experiments/configs/evolve_smoke_mock.json --seed 0 --out experiments/results/evolve_smoke_chopin | tail -3
echo "ALL OK. Next:  python src/llm_evolve.py --config experiments/configs/evolve_local_T3.json --seed 0 --out experiments/results/evolve/local_T3_s0"
