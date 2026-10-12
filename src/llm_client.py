"""Minimal LLM client: Ollama (local) or any OpenAI-compatible chat API. Logs every call.

    from llm_client import LLMClient
    llm = LLMClient.from_config({"provider": "ollama", "model": "qwen2.5-coder:7b"})
    text, usage = llm.chat("system prompt", "user prompt")

Config keys:
    provider   "ollama" | "openai"
    model      model name
    base_url   ollama: http://localhost:11434 (default); openai: e.g. https://api.openai.com/v1
    api_key    openai only (or env var OPENAI_API_KEY / LLM_API_KEY)
    temperature, max_tokens, timeout_s
    price_in, price_out   USD per 1M tokens (for cost reporting; 0 for local)
"""
from __future__ import annotations
import json, os, time, urllib.request, urllib.error
from dataclasses import dataclass, field


@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    seconds: float = 0.0
    cost_usd: float = 0.0


class LLMClient:
    def __init__(self, provider: str, model: str, base_url: str | None = None, api_key: str | None = None,
                 temperature: float = 0.8, max_tokens: int = 1200, timeout_s: int = 180,
                 price_in: float = 0.0, price_out: float = 0.0, log_path: str | None = None):
        self.provider, self.model = provider, model
        self.base_url = (base_url or ("http://localhost:11434" if provider == "ollama" else "https://api.openai.com/v1")).rstrip("/")
        self.api_key = api_key or os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
        self.temperature, self.max_tokens, self.timeout_s = temperature, max_tokens, timeout_s
        self.price_in, self.price_out = price_in, price_out
        self.log_path = log_path
        self.total = Usage(); self.n_calls = 0

    @classmethod
    def from_config(cls, cfg: dict, log_path: str | None = None):
        return cls(**{k: v for k, v in cfg.items() if k in cls.__init__.__code__.co_varnames}, log_path=log_path)

    def _post(self, url: str, payload: dict, headers: dict) -> dict:
        req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json", **headers})
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout_s) as r:
                    return json.loads(r.read().decode())
            except (urllib.error.URLError, TimeoutError) as e:
                if attempt == 2: raise
                time.sleep(2 * (attempt + 1))

    def chat(self, system: str, user: str, temperature: float | None = None) -> tuple[str, Usage]:
        t0 = time.time()
        temp = self.temperature if temperature is None else temperature
        if self.provider == "mock":          # plumbing test without a model: random small variants of a heuristic
            import random
            r = random.Random(self.n_calls)
            if "Output only the reflection" in user or "Output only the list" in user:
                text = "- prefer small distance and small turn angle\n- penalise candidates that do not fit the battery"
            else:
                w, k = r.choice([0.1, 0.25, 0.5]), r.choice([0.5, 1.0, 2.0])
                bad = r.random() < 0.15
                body = "    return np.zeros_like(dist_m)" if bad else f"    return 1.0 / (dist_m + {w} * turn_deg + 1.0) ** {k} * np.where(fits > 0.5, 1.0, 0.2)"
                text = f"{{mock variant w={w} k={k}}}\n```python\nimport numpy as np\n\ndef heuristic(dist_m, turn_deg, swath_len_m, energy_left_frac, depot_dist_m, fits):\n{body}\n```"
            u = Usage(100, 80)
        elif self.provider == "ollama":
            out = self._post(f"{self.base_url}/api/chat", {
                "model": self.model, "stream": False,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "options": {"temperature": temp, "num_predict": self.max_tokens}}, {})
            text = out["message"]["content"]
            u = Usage(out.get("prompt_eval_count", 0), out.get("eval_count", 0))
        else:
            out = self._post(f"{self.base_url}/chat/completions", {
                "model": self.model, "temperature": temp, "max_tokens": self.max_tokens,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]},
                {"Authorization": f"Bearer {self.api_key}"})
            text = out["choices"][0]["message"]["content"]
            uu = out.get("usage", {})
            u = Usage(uu.get("prompt_tokens", 0), uu.get("completion_tokens", 0))
        u.seconds = time.time() - t0
        u.cost_usd = (u.prompt_tokens * self.price_in + u.completion_tokens * self.price_out) / 1e6
        self.n_calls += 1
        self.total.prompt_tokens += u.prompt_tokens; self.total.completion_tokens += u.completion_tokens
        self.total.seconds += u.seconds; self.total.cost_usd += u.cost_usd
        if self.log_path:
            with open(self.log_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps({"t": time.time(), "model": self.model, "system": system, "user": user, "response": text,
                                     "usage": u.__dict__}) + "\n")
        return text, u

    def summary(self) -> dict:
        return {"provider": self.provider, "model": self.model, "calls": self.n_calls, **self.total.__dict__}


def extract_code(text: str) -> str:
    """Pull the python code block out of an LLM reply (first ```python ... ``` block, else whole text)."""
    import re
    m = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.S)
    return (m.group(1) if m else text).strip()
