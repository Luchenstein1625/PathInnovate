"""Conexion opcional a un LLM por .env: OpenAI, Hugging Face (router OpenAI-compatible) o Anthropic. Sin dependencias extra salvo `anthropic` si se usa."""
import json, os, urllib.request
from pathlib import Path

BASES = {"openai": "https://api.openai.com/v1", "huggingface": "https://router.huggingface.co/v1"}
KEYS = {"openai": "OPENAI_API_KEY", "huggingface": "HF_TOKEN", "anthropic": "ANTHROPIC_API_KEY"}

def load_env(path: str = ".env") -> None:
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

def complete(prompt: str, max_tokens: int = 1200) -> str:
    load_env()
    prov = os.environ.get("LLM_PROVIDER", "").lower()
    if prov not in KEYS:
        raise SystemExit("Define LLM_PROVIDER (openai | huggingface | anthropic) en .env. Ver .env.example")
    key = os.environ.get("LLM_API_KEY") or os.environ.get(KEYS[prov])
    model = os.environ.get("LLM_MODEL")
    if not key or not model:
        raise SystemExit(f"Faltan LLM_MODEL y la clave ({KEYS[prov]} o LLM_API_KEY) en .env")
    if prov == "anthropic":
        import anthropic
        m = anthropic.Anthropic(api_key=key).messages.create(model=model, max_tokens=max_tokens,
                                                              messages=[{"role": "user", "content": prompt}])
        return m.content[0].text
    base = os.environ.get("LLM_BASE_URL", BASES[prov]).rstrip("/")
    body = json.dumps({"model": model, "max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(base + "/chat/completions", body,
                                 {"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)["choices"][0]["message"]["content"]
