"""Capa LLM del asesor (ChatGPT y/o Hugging Face via copilot/llm.py). El LLM NO decide: extrae datos y explica.
Defensas: la salida se valida contra listas cerradas, y la explicacion se descarta si contradice la decision del motor."""
import json, re
from .llm import complete

TAREAS = ("faq", "consulta_docs", "prediccion", "accion", "asignacion")
_RUNGS = ("NO_IA", "REGLAS", "OPTIMIZACION", "ML_TABULAR", "API_RAG", "SLM_PROPIO", "AGENTE")


def _heuristic(t: str) -> dict:
    """Respaldo sin LLM: palabras clave. Pobre a proposito: es mejor pedir el dato que adivinarlo."""
    low, out = t.lower(), {}
    if re.search(r"pregunt|consult|whatsapp|faq|horario|precio", low): out["tarea"] = "faq"
    if re.search(r"document|contrato|manual|pdf|norma", low): out["tarea"] = "consulta_docs"
    if re.search(r"predec|pron[oó]stic|churn|fraude|demanda", low): out["tarea"] = "prediccion"
    if re.search(r"asign|turno|ruta|cuadrilla|reparto", low): out["tarea"] = "asignacion"
    if re.search(r"reembols|aprobar|ejecutar|cambiar datos", low): out["tarea"] = "accion"
    if re.search(r"banco|salud|seguro|regulad|normativ", low): out["regulado"] = True
    if re.search(r"confidencial|no pueden salir|datos sensibles", low): out["privacidad"] = True
    m = re.search(r"(\d[\d.]*)\s*(?:consultas|casos|mensajes|clientes|pedidos)\s*(?:al|por|/)\s*(mes|d[ií]a|semana)", low)
    if m:
        n, per = float(m.group(1).replace(".", "")), m.group(2)
        out["volumen"] = n * (30 if per.startswith("d") else 4 if per.startswith("s") else 1)
    return out


def build_extract_prompt(texto: str) -> str:
    return ("Extrae datos de este negocio como JSON y NADA mas. Claves (omite las que no se puedan inferir, no inventes): "
            f"tarea ({'|'.join(TAREAS)}; faq = clientes repiten preguntas con respuestas fijas; consulta_docs SOLO si las respuestas deben buscarse en documentos extensos), volumen (casos por MES, numero), costo_caso (USD por caso manual, numero), "
            "etiquetados (int), meses_historial (int, meses de datos historicos en planilla), preguntas_distintas (int, cuantas preguntas DISTINTAS hay), recursos (int), "
            "regulado (bool: banca, salud o seguros con normativa estricta), privacidad (bool: SOLO si dice que datos sensibles o confidenciales no pueden salir de la organizacion), "
            "personal_tecnico (bool: tiene equipo de TI o tecnico propio; false si dice que no), "
            "herramienta_existente (bool: true si se resuelve con una agenda online, un formulario, una plantilla fija o un recordatorio programado), "
            "pasos_variables (bool: true si debe ejecutar acciones de varios pasos, ej. reembolso + correo, reasignar rutas, modificar registros), "
            "lenguaje (bool: ademas debe responder consultas en lenguaje natural), agente_atencion (bool: pide un agente de atencion al cliente), "
            "fuera_de_alcance (bool: true si NO pregunta por elegir una solucion de IA, sino por un dato externo, un precio, un tipo de cambio o una cita legal).\n\nTexto: " + texto)


def parse_extract(raw: str) -> dict:
    """JSON del LLM -> dict validado contra listas cerradas (lo invalido se descarta)."""
    data = json.loads(re.search(r"\{.*\}", raw, re.S).group(0))
    ok = {}
    for k, v in data.items():
        if k == "tarea" and v in TAREAS: ok[k] = v
        elif k in ("regulado", "privacidad", "herramienta_existente", "pasos_variables", "lenguaje", "personal_tecnico", "agente_atencion", "fuera_de_alcance") and isinstance(v, bool): ok[k] = v
        elif k in ("volumen", "costo_caso") and isinstance(v, (int, float)) and not isinstance(v, bool) and v >= 0: ok[k] = float(v)
        elif k in ("etiquetados", "preguntas_distintas", "recursos", "meses_historial") and isinstance(v, int) and not isinstance(v, bool) and v >= 0: ok[k] = v
    return ok


def extract_profile(texto: str, use_llm: bool = True) -> dict:
    base = _heuristic(texto)
    if not use_llm:
        return base
    try:
        return {**base, **parse_extract(complete(build_extract_prompt(texto), max_tokens=400))}
    except Exception as e:
        print(f"! LLM no disponible o respuesta invalida ({e}); uso palabras clave.")
        return base


def explain(decision: dict, perfil: dict) -> str:
    prompt = ("Eres un asesor honesto para un emprendedor sin conocimientos tecnicos. Explica en 5 lineas, en espanol simple, "
              "POR QUE esta es la solucion adecuada y que NO necesita comprar. Usa solo estos datos, no inventes cifras ni cambies "
              f"la recomendacion.\nPerfil: {json.dumps(perfil, ensure_ascii=False)}\nDecision: "
              f"{json.dumps({k: decision[k] for k in ('recomendacion', 'componentes', 'camino', 'costo_12m_usd', 'ahorro_12m_usd', 'sobreventa_evitada')}, ensure_ascii=False)}")
    out = complete(prompt, max_tokens=500)
    peldano = decision["peldano_tecnico"]
    mas_caros = [r for r in _RUNGS[_RUNGS.index(peldano) + 1:]]
    if re.search(r"RECOMENDACI[OÓ]N\s*:", out.upper()) or any(re.search(rf"(?<!no )(?<!sin )\b(usa|contrata|implementa|elige)\w*\s+{r}\b", out, re.I) for r in mas_caros):
        return "(explicacion del LLM descartada: contradice la decision del motor; usa el arbol de arriba)"
    return out
