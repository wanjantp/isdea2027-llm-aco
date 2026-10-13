#!/usr/bin/env bash
# Install/upgrade a USER-level Ollama (no sudo) and run it on port 11435, independent of any system service on 11434.
set -e
VER=${1:-v0.40.3}
mkdir -p ~/bin ~/ollama_models ~/ollama_pkg
cd ~/ollama_pkg
URL="https://github.com/ollama/ollama/releases/download/$VER/ollama-linux-amd64.tgz"
echo "downloading $URL"
curl -fL --retry 3 -o ollama.tgz "$URL"
ls -la ollama.tgz
tar -xzf ollama.tgz
# archive layout has changed across versions: find the binary wherever it landed
BIN=$(find . -maxdepth 3 -type f -name ollama | head -1)
cp "$BIN" ~/bin/ollama && chmod +x ~/bin/ollama
# keep bundled libraries (CUDA runners) next to the binary if present
[ -d ./lib ] && rm -rf ~/bin/lib && cp -r ./lib ~/bin/lib || true
~/bin/ollama --version
grep -q OLLAMA_BASE_URL ~/.bashrc || cat >> ~/.bashrc <<'EOB'
export PATH=~/bin:$PATH
export OLLAMA_MODELS=~/ollama_models
export OLLAMA_HOST=127.0.0.1:11435
export OLLAMA_BASE_URL=http://127.0.0.1:11435
export OLLAMA_MAX_LOADED_MODELS=1
EOB
export PATH=~/bin:$PATH OLLAMA_MODELS=~/ollama_models OLLAMA_HOST=127.0.0.1:11435 OLLAMA_BASE_URL=http://127.0.0.1:11435 OLLAMA_MAX_LOADED_MODELS=1
pkill -u "$USER" -f "bin/ollama serve" 2>/dev/null || true
nohup ~/bin/ollama serve > ~/ollama_user.log 2>&1 &
sleep 6
curl -s http://127.0.0.1:11435/api/version
~/bin/ollama pull qwen3.5:9b
~/bin/ollama list
echo "user-level Ollama $VER running on 127.0.0.1:11435; models in ~/ollama_models"
