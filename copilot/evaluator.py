"""Benchmark reproducible de 4 configuraciones sobre un conjunto fijo de preguntas.
  llm_solo  : OpenAI sin contexto (linea base sin RAG ni verificador)
  rag_openai: OpenAI + RAG, sin verificador
  rag_local : Qwen local + RAG, sin verificador
  hibrido   : OpenAI + RAG + verificador (citas y cifras) + 1 reintento + abstencion
Cada metrica sale de la corrida; nada esta escrito a mano."""
import datetime, json, math, platform, re, statistics, unicodedata
from pathlib import Path
from typing import Any, Dict, List

from copilot.verifier import GroundingVerifier

ROOT = Path(__file__).resolve().parent.parent
SENT = "NO_HAY_INFORMACION"
SYS_RAG = ("Responde SOLO con el contexto. Cita cada afirmación con su número entre corchetes, p. ej. [1]. "
           f"Si el contexto no contiene la respuesta, responde exactamente {SENT}.\nContexto:\n{{ctx}}")
SYS_SOLO = "Eres un asistente del Magíster en IA de la UAI. Responde breve y directo."
LABELS = {
    "llm_solo": ("OpenAI sin RAG", "Línea base: LLM sin contexto ni verificador"),
    "rag_openai": ("OpenAI + RAG", "gpt-4o-mini con contexto, sin verificador"),
    "rag_local": ("Qwen2.5-1.5B + RAG", "Modelo abierto local con contexto, sin verificador"),
    "hibrido": ("Híbrido verificado", "RAG + verificador de citas/cifras + reintento + abstención"),
    "hibrido_local": ("Qwen + verificador", "SLM local + RAG + verificador + reintento + abstención"),
}
_STOP = set("de la el los las un una y o en a que es se por con para del al cual cuales cuantos cuantas como cuando qué".split())


def norm(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")


def retrieve(q: str, corpus: List[Dict[str, str]], k: int = 3) -> List[Dict[str, str]]:
    qt = {t for t in re.findall(r"\w+", norm(q)) if len(t) > 2 and t not in _STOP}
    sc = [(len(qt & set(re.findall(r"\w+", norm(c["text"])))), -i, c) for i, c in enumerate(corpus)]
    return [c for _, _, c in sorted(sc, key=lambda x: (x[0], x[1]), reverse=True)[:k]]


def _abstains(ans: str) -> bool:
    return SENT in ans or bool(re.search(r"\bno (hay|tengo|se indica|aparece|encuentro|dispongo|puedo)", norm(ans)))


def score(q: Dict[str, Any], ans: str, chunks, needs_cit: bool) -> Dict[str, Any]:
    ab = _abstains(ans)
    cit = None if not needs_cit else (True if ab else GroundingVerifier.verify_citations(ans, chunks)[0])
    facts = True if ab else GroundingVerifier.verify_facts(ans, chunks)[0]
    correct = ab if q.get("abstain") else (not ab and all(re.search(g, norm(ans)) for g in q["gold"]))
    return {"abstained": ab, "citas_ok": cit, "cifras_ok": facts, "correcta": bool(correct),
            "alucinacion": (not ab) and (not facts),          # cifra inventada
            "sin_cita": bool(needs_cit and not ab and not cit)}  # cita ausente o inexistente


def _check(ans, chunks):
    if _abstains(ans):
        return True, []
    ok1, e1 = GroundingVerifier.verify_citations(ans, chunks)
    ok2, e2 = GroundingVerifier.verify_facts(ans, chunks)
    return ok1 and ok2, e1 + e2


def _run_one(cfg, runner, q, chunks):
    ctx = "\n".join(f"[{i + 1}] {c['text']}" for i, c in enumerate(chunks))
    sysp = SYS_RAG.format(ctx=ctx)
    pack = lambda r: (r.answer, r.latency_seconds, r.cost_usd, (r.prompt_tokens, r.completion_tokens))
    if cfg == "llm_solo":
        return (*pack(runner.generate_openai(q["q"], SYS_SOLO)), 0, False)
    if cfg == "rag_openai":
        return (*pack(runner.generate_openai(q["q"], sysp)), 0, False)
    if cfg == "rag_local":
        return (*pack(runner.generate_local_hf(q["q"], sysp)), 0, False)
    gen = runner.generate_local_hf if cfg == "hibrido_local" else runner.generate_openai
    ans, lat, cost, tok = pack(gen(q["q"], sysp))
    retries, repaired = 0, False
    ok, issues = _check(ans, chunks)
    if not ok:  # 1) reparación simbólica sin costo: adjuntar citas respaldadas
        fixed = GroundingVerifier.attach_citations(ans, chunks)
        if fixed != ans and _check(fixed, chunks)[0]:
            ans, ok, repaired = fixed, True, True
    if not ok:  # 2) un reintento con retroalimentación
        retries = 1
        fb = f"{q['q']}\n\nTu respuesta anterior tuvo problemas: {'; '.join(issues)}. Reescribe usando solo el contexto con citas válidas, o responde {SENT}."
        a2, l2, c2, t2 = pack(gen(fb, sysp))
        lat += l2; cost += c2; tok = (tok[0] + t2[0], tok[1] + t2[1]); ans = a2
        if not _check(ans, chunks)[0]:
            fixed = GroundingVerifier.attach_citations(ans, chunks)
            if fixed != ans and _check(fixed, chunks)[0]:
                ans, repaired = fixed, True
            else:
                ans = SENT  # 3) abstención
    return ans, round(lat, 3), round(cost, 6), tok, retries, repaired


def _pct(v: List[float], p: float) -> float:
    s = sorted(v); return round(s[max(0, math.ceil(p * len(s)) - 1)], 3) if s else 0.0


def summarize(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    n = len(rows)
    if not n:
        return {"n": 0}
    rate = lambda k: round(sum(1 for r in rows if r[k]) / n, 3)
    cits = [r["citas_ok"] for r in rows if r["citas_ok"] is not None]
    return {"n": n, "latencia_p50_s": _pct([r["latency"] for r in rows], .5), "latencia_p95_s": _pct([r["latency"] for r in rows], .95),
            "costo_medio_usd": round(statistics.mean(r["cost"] for r in rows), 6),
            "tokens_medios": round(statistics.mean(r["tokens"] for r in rows), 1),
            "tokens_in_medios": round(statistics.mean(r["tok_in"] for r in rows), 1),
            "tokens_out_medios": round(statistics.mean(r["tok_out"] for r in rows), 1),
            "correctas": rate("correcta"), "alucinacion": rate("alucinacion"), "abstenciones": rate("abstained"), "sin_cita": rate("sin_cita"), "reparadas": rate("reparada"),
            "cifras_ok": rate("cifras_ok"), "citas_ok": round(sum(cits) / len(cits), 3) if cits else None,
            "reintentos": round(sum(r["retries"] for r in rows) / n, 3)}


def run_benchmark(runner, preguntas, corpus, repeats=1, include_local=True, k=3) -> Dict[str, Any]:
    cfgs = [c for c in LABELS if include_local or c not in ("rag_local", "hibrido_local")]
    rows = {c: [] for c in cfgs}; resp: Dict[str, Dict[str, Any]] = {}; errors = []
    for q in preguntas:
        chunks = retrieve(q["q"], corpus, k)
        for rep in range(repeats):
            for c in cfgs:
                try:
                    ans, lat, cost, tok, ret, rep_ = _run_one(c, runner, q, chunks)
                except Exception as e:  # una falla no invalida la corrida
                    errors.append({"cfg": c, "q": q["id"], "error": str(e)[:200]}); continue
                row = {"qid": q["id"], "rep": rep, "answer": ans, "latency": lat, "cost": cost, "tok_in": tok[0], "tok_out": tok[1], "tokens": tok[0] + tok[1], "retries": ret, "reparada": rep_,
                       **score(q, ans, chunks, c != "llm_solo")}
                rows[c].append(row)
                if rep == 0:
                    resp.setdefault(q["id"], {})[c] = row
    return {"meta": {"fecha": datetime.datetime.now().isoformat(timespec="seconds"), "dispositivo": getattr(runner, "device_label", "n/a"),
                     "modelo_openai": getattr(runner, "openai_model", "?"), "modelo_local": getattr(runner, "local_model_id", "?"),
                     "n_preguntas": len(preguntas), "repeticiones": repeats, "k_contexto": k, "python": platform.python_version(),
                     "nota": "Resultados medidos. alucinacion = cifra sin respaldo en el contexto recuperado o cita inexistente (proxy)."},
            "configs": {c: {"label": LABELS[c][0], "desc": LABELS[c][1], "metricas": summarize(rows[c])} for c in cfgs},
            "preguntas": [{"id": q["id"], "q": q["q"]} for q in preguntas], "respuestas": resp, "errores": errors}


def load_eval(root: Path = ROOT):
    pre = []
    for f in sorted((root / "eval").glob("preguntas*.json")):   # preguntas.json, _extra, _dificiles...
        pre += json.loads(f.read_text(encoding="utf-8"))
    return pre, json.loads((root / "eval/corpus.json").read_text(encoding="utf-8"))


def write_outputs(res: Dict[str, Any], root: Path = ROOT) -> None:
    txt = json.dumps(res, ensure_ascii=False, indent=2)
    (root / "eval").mkdir(exist_ok=True)
    (root / "eval/resultados.json").write_text(txt, encoding="utf-8")
    (root / "resultados.js").write_text("window.RESULTADOS = " + txt + ";\n", encoding="utf-8")
