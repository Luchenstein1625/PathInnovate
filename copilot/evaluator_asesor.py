"""Benchmark en el dominio de PathInnovate: ¿recomienda la solución justa o una sobredimensionada?
Etiquetas: NO_IA < REGLAS < ML_TABULAR/API_RAG < SLM_PROPIO < AGENTE. Las 5 configuraciones son las de evaluator.py.
Limitación declarada: el corpus son reglas del grupo (supuestos a validar) y las etiquetas de referencia las fijó el
grupo; mide recuperación + aplicación de reglas, no la calidad de un experto externo."""
import datetime, json, platform, re
from pathlib import Path
from typing import Any, Dict, List

from copilot.evaluator import LABELS, retrieve, summarize
from copilot.verifier import GroundingVerifier

ROOT = Path(__file__).resolve().parent.parent
NOINFO = "NO_HAY_INFORMACION"
RANK = {"NO_IA": 0, "REGLAS": 1, "ML_TABULAR": 2, "API_RAG": 2, "SLM_PROPIO": 3, "AGENTE": 4}
ETQ = ", ".join(RANK)
COMP = ("REGLAS", "ML_TABULAR", "API_RAG", "SLM_PROPIO", "VERIFICADOR", "HUMANO")
_BASE = ("Eres un orientador que recomienda la solución de IA MÁS SIMPLE que resuelve el problema de un emprendedor. "
         f"Primera línea exacta: RECOMENDACION: <ETIQUETA> (una de {ETQ}) cuando se pide elegir una solución; o, si se pide una arquitectura, comparar opciones o la necesidad combina varias capacidades (responder, predecir, ejecutar acciones, cumplir normativa), COMPONENTES: <lista separada por comas con etiquetas de {', '.join(COMP)}>, solo los necesarios. Luego 1 o 2 frases que lo justifiquen")
SYS_ASESOR = _BASE + f", citando [n]. Usa SOLO el contexto. Si el contexto no alcanza, responde solo RECOMENDACION: {NOINFO}.\nContexto:\n{{ctx}}"
SYS_SOLO = _BASE + "."


def label(ans: str):
    m = re.search(r"RECOMENDACI[OÓ]N:\s*([A-Z_]+)", ans.upper())
    return m.group(1) if m else None


def parse(ans):
    first = ans.strip().splitlines()[0].upper() if ans.strip() else ""
    m = re.search(r"COMPONENTES:\s*(.*)", first)
    if m:
        return "C", {t for t in re.findall(r"[A-Z_]+", m.group(1)) if t in COMP}
    r = re.search(r"RECOMENDACI[OÓ]N:\s*(.*)", first)
    if r:  # el modelo listó varios componentes pero usó el prefijo RECOMENDACION
        toks = {t for t in re.findall(r"[A-Z_]+", r.group(1).split(". ")[0]) if t in COMP}
        if len(toks) >= 2:
            return "C", toks
    lab = label(ans)
    return ("R", lab) if lab else (None, None)


def fmt_ok(ans):
    k, v = parse(ans)
    return (k == "R" and (v in RANK or v == NOINFO)) or (k == "C" and bool(v))


def _check(ans, chunks, user_text=""):
    if parse(ans) == ("R", NOINFO):
        return True, []
    if not fmt_ok(ans):
        return False, ["Formato: falta una línea RECOMENDACION o COMPONENTES con etiquetas válidas"]
    ok1, e1 = GroundingVerifier.verify_citations(ans, chunks)
    ok2, e2 = GroundingVerifier.verify_facts(ans, chunks, user_text)
    return ok1 and ok2, e1 + e2


def score(q, ans, chunks, needs_cit):
    kind, val = parse(ans); gold = q["gold"]
    lab = "+".join(sorted(val)) if kind == "C" else val
    ab = (kind, val) == ("R", NOINFO)
    pr, gr = RANK.get(lab), RANK.get(gold)
    cit = None if not needs_cit else (True if ab else GroundingVerifier.verify_citations(ans, chunks)[0])
    facts = True if ab else GroundingVerifier.verify_facts(ans, chunks, q.get("q", ""))[0]
    sob = pr is not None and gr is not None and pr > gr
    sub = pr is not None and gr is not None and pr < gr
    ok = lab == gold
    gs = set(q["gold_set"]) if q.get("gold_set") else (
        set(re.findall(r"[A-Z_]+", gold.split(":", 1)[1])) & set(COMP) if gold.startswith("COMPONENTES:") else None)
    parcial = None
    if gs:  # arquitectura compuesta: se compara el conjunto de componentes (con credito parcial Jaccard)
        ps = val if kind == "C" else ({val} & set(COMP) if kind == "R" else set())
        ok, sob, sub = ps == gs, bool(ps - gs), bool(gs - ps) and not ab
        parcial = round(len(ps & gs) / len(ps | gs), 3) if (ps | gs) else 0.0
    return {"gold": gold, "etiqueta": lab, "abstained": ab, "citas_ok": cit, "cifras_ok": facts, "correcta": ok,
            "sobredim": sob, "subdim": sub, "parcial": parcial,
            "invento_fuera": gold == NOINFO and not ab, "alucinacion": (not ab) and (not facts),
            "sin_cita": bool(needs_cit and not ab and not cit)}


def _run_one(cfg, runner, q, chunks):
    ctx = "\n".join(f"[{i + 1}] {c['text']}" for i, c in enumerate(chunks)); sysp = SYS_ASESOR.format(ctx=ctx)
    pack = lambda r: (r.answer, r.latency_seconds, r.cost_usd, (r.prompt_tokens, r.completion_tokens))
    if cfg == "llm_solo":
        return (*pack(runner.generate_openai(q["q"], SYS_SOLO)), 0, False)
    if cfg == "rag_openai":
        return (*pack(runner.generate_openai(q["q"], sysp)), 0, False)
    if cfg == "rag_local":
        return (*pack(runner.generate_local_hf(q["q"], sysp)), 0, False)
    gen = runner.generate_local_hf if cfg == "hibrido_local" else runner.generate_openai
    ans, lat, cost, tok = pack(gen(q["q"], sysp)); retries, repaired = 0, False
    ok, issues = _check(ans, chunks, q["q"])
    if not ok and fmt_ok(ans):                # 1) reparación simbólica de citas
        fixed = GroundingVerifier.attach_citations(ans, chunks)
        if fixed != ans and _check(fixed, chunks, q["q"])[0]:
            ans, ok, repaired = fixed, True, True
    if not ok:                                  # 2) reintento con retroalimentación
        retries = 1
        a2, l2, c2, t2 = pack(gen(f"{q['q']}\n\nTu respuesta anterior tuvo problemas: {'; '.join(issues)}. Corrige usando solo el contexto.", sysp))
        lat += l2; cost += c2; tok = (tok[0] + t2[0], tok[1] + t2[1]); ans = a2
        if not _check(ans, chunks, q["q"])[0]:
            fixed = GroundingVerifier.attach_citations(ans, chunks)
            if fmt_ok(ans) and fixed != ans and _check(fixed, chunks, q["q"])[0]:
                ans, repaired = fixed, True
            else:
                ans = f"RECOMENDACION: {NOINFO}"  # 3) abstención
    return ans, round(lat, 3), round(cost, 6), tok, retries, repaired


def _extra(rows):
    resp = [r for r in rows if r["gold"] != NOINFO]; n = len(resp) or 1; fuera = [r for r in rows if r["gold"] == NOINFO] or [None]
    comp = [r for r in rows if r.get("parcial") is not None]
    return {"n_con_respuesta": len(resp), "sobredimensionadas": round(sum(r["sobredim"] for r in resp) / n, 3),
            "subdimensionadas": round(sum(r["subdim"] for r in resp) / n, 3),
            "inventa_fuera_de_corpus": round(sum(bool(r and r["invento_fuera"]) for r in fuera) / len(fuera), 3),
            "n_sobredim": sum(r["sobredim"] for r in resp), "n_correctas": sum(r["correcta"] for r in rows),
            "n_compuestas": len(comp), "parcial_compuestas": round(sum(r["parcial"] for r in comp) / len(comp), 3) if comp else None}


def run_benchmark_asesor(runner, preguntas, corpus, repeats=1, include_local=True, k=5) -> Dict[str, Any]:
    cfgs = [c for c in LABELS if include_local or c not in ("rag_local", "hibrido_local")]
    rows = {c: [] for c in cfgs}; resp: Dict[str, Dict[str, Any]] = {}; errors = []; hit = []
    for q in preguntas:
        chunks = retrieve(q["q"], corpus, k)
        if q.get("regla"):
            hit.append(q["regla"] in [c["id"] for c in chunks])
        for rep in range(repeats):
            for c in cfgs:
                try:
                    ans, lat, cost, tok, ret, rp = _run_one(c, runner, q, chunks)
                except Exception as e:
                    errors.append({"cfg": c, "q": q["id"], "error": str(e)[:200]}); continue
                row = {"qid": q["id"], "rep": rep, "answer": ans, "latency": lat, "cost": cost, "tok_in": tok[0], "tok_out": tok[1],
                       "tokens": tok[0] + tok[1], "retries": ret, "reparada": rp, **score(q, ans, chunks, c != "llm_solo")}
                rows[c].append(row)
                if rep == 0:
                    resp.setdefault(q["id"], {})[c] = row
    return {"meta": {"dominio": "asesoría de innovación con IA para emprendedores", "fecha": datetime.datetime.now().isoformat(timespec="seconds"),
                     "dispositivo": getattr(runner, "device_label", "n/a"), "modelo_openai": getattr(runner, "openai_model", "?"),
                     "modelo_local": getattr(runner, "local_model_id", "?"), "n_preguntas": len(preguntas), "repeticiones": repeats,
                     "k_contexto": k, "recall_regla_correcta_en_top_k": round(sum(hit) / len(hit), 3) if hit else None,
                     "python": platform.python_version(),
                     "nota": "Reglas y etiquetas definidas por el grupo (supuestos a validar con un experto). sobredimensionada = etiqueta de mayor complejidad que la de referencia."},
            "configs": {c: {"label": LABELS[c][0], "desc": LABELS[c][1], "metricas": {**summarize(rows[c]), **_extra(rows[c])}} for c in cfgs},
            "preguntas": [{"id": q["id"], "q": q["q"], "gold": q["gold"]} for q in preguntas], "respuestas": resp, "errores": errors}
