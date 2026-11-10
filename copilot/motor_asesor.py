"""Configuracion 'motor_reglas' del benchmark del asesor: extractor (LLM barato o palabras clave) + arbol de decision
determinista (advisor.decide). Se mide con las MISMAS preguntas, etiquetas y metricas que las otras 5 configuraciones.
Si no puede determinar la tarea, se abstiene (NO_HAY_INFORMACION) en vez de adivinar.
Limitacion declarada: las reglas del motor y las etiquetas de referencia salen del mismo grupo; la prueba justa es el
conjunto externo (eval_asesor/preguntas_externas.json), que las reglas no vieron al escribirse."""
from .advisor import decide, profile_args
from .asesor_llm import _heuristic, build_extract_prompt, parse_extract
from .evaluator_asesor import NOINFO, _extra, score
from .evaluator import summarize

LABEL = "Motor de reglas (asesor)"
DESC = "Extractor LLM + arbol de decision determinista, sin RAG ni generacion libre"
NEUTRO = {"volumen": 1000.0, "costo_caso": 2.0}   # las preguntas no traen cifras; solo se compara el peldano, no el pago


def answer_for(q: dict, runner=None):
    """-> (respuesta, latencia_s, costo_usd, tokens_in, tokens_out)"""
    texto, lat, cost, tin, tout = q["q"], 0.0, 0.0, 0, 0
    perfil = _heuristic(texto)
    if runner is not None:
        try:
            r = runner.generate_openai(build_extract_prompt(texto))
            perfil.update(parse_extract(r.answer)); lat, cost, tin, tout = r.latency_seconds, r.cost_usd, r.prompt_tokens, r.completion_tokens
        except Exception:
            pass                                   # sin LLM: se queda con palabras clave
    if perfil.get("fuera_de_alcance") or (not perfil.get("tarea") and not perfil.get("herramienta_existente")):
        return f"RECOMENDACION: {NOINFO}", lat, cost, tin, tout
    perfil.setdefault("tarea", "faq")
    for k, v in NEUTRO.items(): perfil.setdefault(k, v)
    d = decide(**profile_args(perfil))
    comps = d["componentes"]
    if set(comps) == {"AGENTE", "HUMANO"}:         # en el corpus el humano que valida es parte de la definicion de AGENTE (r6)
        linea = "RECOMENDACION: AGENTE"
    else:
        linea = ("COMPONENTES: " + ", ".join(comps)) if len(comps) > 1 else f"RECOMENDACION: {comps[0]}"
    return linea, lat, cost, tin, tout


def add_config(res: dict, preguntas: list, runner=None) -> dict:
    rows = []
    for q in preguntas:
        ans, lat, cost, tin, tout = answer_for(q, runner)
        row = {"qid": q["id"], "rep": 0, "answer": ans, "latency": round(lat, 3), "cost": round(cost, 6), "tok_in": tin, "tok_out": tout,
               "tokens": tin + tout, "retries": 0, "reparada": False, **score(q, ans, [], False)}
        rows.append(row); res["respuestas"].setdefault(q["id"], {})["motor_reglas"] = row
    res["configs"]["motor_reglas"] = {"label": LABEL, "desc": DESC, "metricas": {**summarize(rows), **_extra(rows)}}
    res["meta"]["motor_reglas"] = "extractor " + ("LLM (" + getattr(runner, "openai_model", "?") + ")" if runner else "palabras clave") + " + decide()"
    return res
