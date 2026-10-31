"""Idea -> propuesta de solucion de IA, con tecnicas elegidas por reglas y evidencia citada de las clases del magister."""
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from .engine_taai2 import BudgetCalculator, STRATEGIES, SymbolicVerifier, chain_reliability, strips_plan, optimize_assignment
from .index import cite

# (id, palabras que activan la regla, componente, tecnica, consulta para buscar evidencia en las clases)
RULES = [
    ("texto", r"consulta|reclamo|document|correo|chat|texto|atenci[oó]n|asistente|contrato|lenguaje",
     "Modelo de lenguaje", "SLM/LLM + RAG; destilacion o LoRA si el volumen justifica un modelo propio",
     "RAG recuperacion LLM SLM destilacion tokens contexto"),
    ("tabular", r"predec|predicci|riesgo|scoring|churn|demanda|fraude|hist[oó]rico|tabular|probabilidad|pron[oó]stico",
     "Modelo predictivo tabular", "ML clasico (Random Forest / Gradient Boosting): datos estructurados y pocos ejemplos, mas barato y explicable que un LLM",
     "random forest arbol de decision aprendizaje supervisado clasificacion"),
    ("vision", r"imagen|foto|video|visual|camara|c[aá]mara|inspecci[oó]n",
     "Modelo de vision", "VLM / modelo multimodal o CNN de dominio", "vision computacional multimodal imagen"),
    ("reglas", r"norma|regla|regulaci|legal|pol[ií]tica|compliance|cumplimiento|auditor|limite|l[ií]mite|presupuesto",
     "Verificador simbolico", "Reglas duras / ontologia que validan o bloquean lo que genera el modelo",
     "reglas ontologia verificacion simbolico neurosimbolico alucinacion"),
    ("asignar", r"asign|program|ruta|turno|cuadrilla|reparto|agenda|calendario|prioriz|capacidad",
     "Optimizador", "Funcion objetivo + restricciones; busqueda local / recocido simulado / solver; LLM solo para formular y explicar",
     "optimizacion algoritmo genetico recocido simulado funcion objetivo restricciones"),
    ("secuencia", r"proceso|flujo|pasos|secuencia|workflow|tramite|tr[aá]mite|replanific|etapas",
     "Planificador", "STRIPS/PDDL o HTN con replanificacion; el LLM propone, el planificador verifica",
     "planificacion STRIPS PDDL HTN replanificacion"),
    ("autonomia", r"ejecut|derivar|aprobar|autom[aá]tic|decide|decisi[oó]n|acci[oó]n|agente",
     "Orquestador de agentes", "Agentes con herramientas; humano en el circuito en acciones irreversibles",
     "agentes autonomia orquestador humano en el circuito confiabilidad"),
]

def select_components(idea: str) -> List[Dict[str, str]]:
    low = idea.lower()
    comps = [dict(id=i, componente=c, tecnica=t, query=q) for i, rx, c, t, q in RULES if re.search(rx, low)]
    if not any(c["id"] == "autonomia" for c in comps):  # la tarea exige algun grado de autonomia
        r = RULES[-1]; comps.append(dict(id=r[0], componente=r[2], tecnica=r[3], query=r[4]))
    if not any(c["id"] in ("texto", "vision") for c in comps):  # y al menos un modelo fundacional
        r = RULES[0]; comps.append(dict(id=r[0], componente=r[2], tecnica=r[3], query=r[4]))
    return comps

def gather_evidence(comps, idx=None, k: int = 2):
    for c in comps:
        hits = idx.search(c["query"], k=k, per_file=1) if idx else []
        c["evidencia"] = [cite(h) for h in hits]
    return comps

def innovate(idea: str, idx=None, queries: int = 50000) -> Dict[str, Any]:
    comps = gather_evidence(select_components(idea), idx)
    calc = BudgetCalculator(monthly_queries=queries)
    evals = {s: calc.evaluate(s) for s in STRATEGIES}
    viable = {s: e for s, e in evals.items() if e["evaluacion_36_meses"]["van_usd"] > 0}
    best = min(viable, key=lambda s: viable[s]["evaluacion_36_meses"]["tco_total_usd"]) if viable else None
    ids = {c["id"] for c in comps}
    ctx = {"latencia_max_ms": 3000, "presupuesto_usd": evals["api"]["evaluacion_12_meses"]["tco_total_usd"],
           "accion_irreversible": "autonomia" in ids, "humano_en_circuito": True}
    sin_evidencia = [c["componente"] for c in comps if not c["evidencia"]]
    return {"idea": idea, "componentes": comps,
            "verificacion": {"reglas_incumplidas": SymbolicVerifier().verify(ctx), "componentes_sin_evidencia_en_clases": sin_evidencia},
            "presupuesto": evals, "alternativa_recomendada": best or "ninguna con VAN positivo a 36 meses",
            "confiabilidad": {"supuesto_precision_por_paso": [0.95, 0.9, 0.92, 0.97],
                              **chain_reliability([0.95, 0.9, 0.92, 0.97], {2: 0.8})},
            "plan_ejemplo": strips_plan(), "optimizacion_ejemplo": optimize_assignment([5, 3, 8, 2, 7, 4, 6, 1], 3)}

def to_markdown(r: Dict[str, Any]) -> str:
    o = [f"# Propuesta de innovacion (borrador)\n\n**Idea:** {r['idea']}\n", "## Componentes y tecnicas (secciones 2 a 6)\n",
         "| Componente | Tecnica elegida | Evidencia en clases |", "|---|---|---|"]
    for c in r["componentes"]:
        o.append(f"| {c['componente']} | {c['tecnica']} | {'<br>'.join(c['evidencia']) or '**SIN EVIDENCIA: citar syllabus o fuente externa**'} |")
    v = r["verificacion"]
    o += ["", "## Verificacion simbolica (seccion 4)", f"- Reglas incumplidas: {v['reglas_incumplidas'] or 'ninguna'}",
          f"- Componentes sin evidencia en clases: {v['componentes_sin_evidencia_en_clases'] or 'ninguno'}",
          "", "## Presupuesto (secciones 8 y 12)", "| Alternativa | TCO 12m | TCO 36m | VAN 36m | Equilibrio (mes) |", "|---|---|---|---|---|"]
    for s, e in r["presupuesto"].items():
        a, b = e["evaluacion_12_meses"], e["evaluacion_36_meses"]
        o.append(f"| {s} | {a['tco_total_usd']:,.0f} | {b['tco_total_usd']:,.0f} | {b['van_usd']:,.0f} | {e['punto_equilibrio_mes']} |")
    o += [f"\n**Alternativa de menor TCO con VAN positivo:** {r['alternativa_recomendada']} (cifras = supuestos a verificar, ver Anexo B).",
          f"\n## Confiabilidad (seccion 3)\nPrecision del flujo {r['confiabilidad']['precision_flujo']} -> con humano {r['confiabilidad']['precision_flujo_con_humano']}.",
          f"\n## Planificacion y optimizacion (secciones 5 y 6)\nPlan: {' -> '.join(r['plan_ejemplo'])}. Makespan greedy {r['optimizacion_ejemplo']['makespan_greedy']} vs SA {r['optimizacion_ejemplo']['makespan_sa']}.",
          "\n> Las tecnicas salen de reglas sobre el texto de la idea; el grupo debe justificarlas y reemplazar los supuestos."]
    return "\n".join(o)

def llm_refine(report_md: str) -> str:
    """Opcional: critica de un LLM configurado en .env (ver copilot/llm.py)."""
    from .llm import complete
    return complete("Critica esta propuesta de solucion de IA: senala tecnicas mal elegidas, riesgos y cifras dudosas. Se concreto.\n\n" + report_md)
