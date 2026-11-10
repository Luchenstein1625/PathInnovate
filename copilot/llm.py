"""LLM opcional por .env. Proveedores: openai (ChatGPT), huggingface (router HF), hf_local (transformers en tu PC), anthropic.
LLM_PROVIDER admite una cadena con respaldo: `openai,huggingface` prueba ChatGPT y, si falla, Hugging Face.
Modelos por proveedor (opcional): LLM_MODEL_OPENAI, LLM_MODEL_HUGGINGFACE, LLM_MODEL_HF_LOCAL; si no, LLM_MODEL."""
import json, os, re, urllib.request
from pathlib import Path

BASES = {"openai": "https://api.openai.com/v1", "huggingface": "https://router.huggingface.co/v1"}
KEYS = {"openai": "OPENAI_API_KEY", "huggingface": "HF_TOKEN", "anthropic": "ANTHROPIC_API_KEY", "hf_local": None}
_PIPES = {}


def load_env(path: str = ".env") -> None:
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.strip()
        if v[:1] in "\"'":                      # valor entre comillas: se respeta tal cual
            v = v.strip(v[0])
        else:                                   # sin comillas: se quita el comentario en linea ("  # ...")
            v = re.split(r"\s+#", v, 1)[0].strip()
        os.environ.setdefault(k.strip(), v)


def providers() -> list:
    load_env()
    return [x.strip().lower() for x in os.environ.get("LLM_PROVIDER", "").split(",") if x.strip()]


def _model(prov: str) -> str:
    por_proveedor = os.environ.get(f"LLM_MODEL_{prov.upper()}")
    if por_proveedor:
        return por_proveedor
    if prov == "openai":   # mismo modelo que usa llm_dual.py en las evaluaciones; no hereda LLM_MODEL (puede ser de otro proveedor)
        return "gpt-4o-mini"
    return os.environ.get("LLM_MODEL", "")


def _clean(txt: str) -> str:
    return re.sub(r"<think>.*?</think>", "", txt or "", flags=re.S).strip()   # modelos con razonamiento (Qwen3, etc.)


def _one(prov: str, prompt: str, max_tokens: int) -> str:
    if prov not in KEYS:
        raise RuntimeError(f"proveedor desconocido: {prov!r} (usa {', '.join(KEYS)})")
    model = _model(prov)
    if not model:
        raise RuntimeError(f"falta LLM_MODEL (o LLM_MODEL_{prov.upper()}) en .env")
    if prov == "hf_local":
        from transformers import pipeline
        pipe = _PIPES.get(model) or _PIPES.setdefault(model, pipeline("text-generation", model=model, device_map="auto"))
        out = pipe([{"role": "user", "content": prompt}], max_new_tokens=max_tokens, do_sample=False)
        return _clean(out[0]["generated_text"][-1]["content"])
    key = os.environ.get("LLM_API_KEY") or os.environ.get(KEYS[prov], "")
    if not key:
        raise RuntimeError(f"falta {KEYS[prov]} en .env")
    if prov == "anthropic":
        import anthropic
        m = anthropic.Anthropic(api_key=key).messages.create(model=model, max_tokens=max_tokens,
                                                              messages=[{"role": "user", "content": prompt}])
        return _clean(m.content[0].text)
    base = os.environ.get("LLM_BASE_URL", BASES[prov]).rstrip("/")
    last = None
    for field in ("max_tokens", "max_completion_tokens"):   # modelos nuevos de OpenAI exigen el segundo
        body = json.dumps({"model": model, field: max_tokens, "messages": [{"role": "user", "content": prompt}]}).encode()
        req = urllib.request.Request(base + "/chat/completions", body,
                                     {"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return _clean(json.load(r)["choices"][0]["message"]["content"])
        except urllib.error.HTTPError as e:
            try:
                detalle = e.read().decode("utf-8", "replace")[:300]
            except Exception:
                detalle = ""
            last = RuntimeError(f"HTTP {e.code} de {prov} (modelo={model!r}): {detalle}")
            if e.code != 400 or "max_" not in detalle:
                break
    raise last or RuntimeError("sin respuesta")


def complete(prompt: str, max_tokens: int = 1200, provider: str = None) -> str:
    """Prueba cada proveedor de la cadena hasta que uno responda. Nunca imprime claves."""
    chain = [provider] if provider else providers()
    if not chain:
        raise SystemExit("Define LLM_PROVIDER (ej. openai,huggingface) en .env. Ver .env.example")
    errs = []
    for prov in chain:
        try:
            return _one(prov, prompt, max_tokens)
        except Exception as e:
            errs.append(f"{prov}: {e}")
    raise RuntimeError("Ningun LLM respondio -> " + " | ".join(errs))
