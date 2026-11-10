"""Asesor anti-sobreventa: recomienda la solucion MAS SIMPLE que alcanza y se paga sola.
La DECISION es determinista (arbol de reglas auditable, sin LLM). El LLM (opcional, ver asesor_llm.py) solo
convierte texto libre en datos y explica; nunca decide ni sube el peldano.

Uso:
  python -m copilot.advisor --tarea faq --volumen 600 --costo-caso 1.5 --preguntas-distintas 15
  python -m copilot.advisor --tarea consulta_docs --volumen 20000 --costo-caso 2 --regulado --privacidad
  python -m copilot.advisor --texto "tengo una panaderia y me preguntan lo mismo por WhatsApp" --llm
Los costos son SUPUESTOS editables: config/advisor_costs.json (mismas claves que COSTS) y verificar precios (Anexo B)."""
import argparse, json, sys
from pathlib import Path

LADDER = ["NO_IA", "REGLAS", "OPTIMIZACION", "ML_TABULAR", "API_RAG", "SLM_PROPIO", "AGENTE"]
# (instalacion USD, fijo mensual USD, variable por caso USD)  -- SUPUESTOS a verificar
COSTS = {"NO_IA": (0, 15, 0.0), "REGLAS": (300, 20, 0.0), "OPTIMIZACION": (1500, 40, 0.0001),
         "ML_TABULAR": (2500, 60, 0.0002), "API_RAG": (1500, 80, 0.0006),
         "SLM_PROPIO": (6000, 450, 0.0001), "AGENTE": (9000, 250, 0.004)}
WHY_NOT = {
    "NO_IA": "no resuelve el problema con las herramientas actuales",
    "REGLAS": "el problema no cabe en un menu o flujo fijo",
    "OPTIMIZACION": "no hay un problema de asignacion con restricciones",
    "ML_TABULAR": "faltan datos etiquetados o la tarea no es predecir",
    "API_RAG": "un modelo de lenguaje no aporta sobre lo que ya resuelve el peldano elegido",
    "SLM_PROPIO": "GPU y mantenimiento fijos no se amortizan con tu volumen y tus datos pueden usar una API con contrato",
    "AGENTE": "agrega costo y error compuesto (precision por paso se multiplica) sin que tu flujo lo necesite",
}
TAREAS = ("faq", "consulta_docs", "prediccion", "accion", "asignacion")


def _costs():
    c = dict(COSTS)
    p = Path("config/advisor_costs.json")
    if p.exists():
        c.update({k: tuple(v) for k, v in json.loads(p.read_text(encoding="utf-8")).items() if k in c})
    return c


def _tco(rung, vol, meses, costs):
    s, f, v = costs[rung]
    return s + meses * (f + v * vol)


def profile_args(perfil: dict) -> dict:
    """Solo las claves que decide() entiende (el extractor puede traer otras, p. ej. fuera_de_alcance)."""
    ok = decide.__code__.co_varnames[:decide.__code__.co_argcount]
    return {k: v for k, v in perfil.items() if k in ok}


def decide(tarea, volumen, costo_caso, etiquetados=0, regulado=False, privacidad=False, preguntas_distintas=None,
           herramienta_existente=False, pasos_variables=False, lenguaje=False, recursos=None, cobertura=0.7,
           personal_tecnico=None, meses_historial=None, agente_atencion=False):
    """Reglas alineadas con el corpus del grupo (eval_asesor/corpus.json, r1-r21). pasos_variables = la accion tiene varios pasos
    (reembolso + correo, reasignar rutas). personal_tecnico: None = no informado (se supone que si)."""
    if tarea not in TAREAS:
        raise ValueError(f"tarea invalida {tarea!r}; usa {TAREAS}")
    costs, camino, comp = _costs(), [], []
    # Guardia anti-sobreventa: pocas preguntas distintas = FAQ, aunque alguien (o un LLM) lo llame "consulta de documentos"
    if tarea == "consulta_docs" and preguntas_distintas is not None and preguntas_distintas < 50 and not privacidad:
        camino.append(f"Dices consulta de documentos, pero solo hay {preguntas_distintas} preguntas distintas (<50): se trata como FAQ")
        tarea = "faq"
    pocas = preguntas_distintas is not None and preguntas_distintas < 50
    if herramienta_existente:
        rung = "NO_IA"; camino.append("Una herramienta existente (agenda, formulario, plantilla, recordatorio programado) ya lo resuelve -> NO_IA")
    elif tarea in ("faq", "consulta_docs") and (privacidad or volumen > 5_000_000) and not pocas:
        motivo = "los datos no pueden salir de la organizacion" if privacidad else f"volumen sostenido de {int(volumen):,} consultas/mes (>5 millones)"
        if personal_tecnico is False:
            rung = "API_RAG"; camino.append(f"{motivo}, pero no hay personal tecnico: servicio administrado (API) con acuerdo de tratamiento de datos antes que infraestructura propia")
        else:
            rung = "SLM_PROPIO"; camino.append(f"{motivo} -> modelo pequeno autoalojado" + ("" if personal_tecnico else " (se supone que hay equipo tecnico; si no lo hay, usa API con acuerdo de datos)"))
    elif tarea == "faq":
        if pocas or preguntas_distintas is None:
            rung = "REGLAS"; camino.append(f"FAQ con menos de 50 preguntas distintas ({preguntas_distintas if preguntas_distintas is not None else 'no informado'}) -> menu o respuestas fijas")
        else:
            rung = "API_RAG"; camino.append("FAQ con 50+ preguntas distintas -> modelo de lenguaje con RAG")
    elif tarea == "consulta_docs":
        rung = "API_RAG"; camino.append("Contenido amplio o que cambia, sin datos sensibles y con menos de 100.000 consultas/mes -> RAG con API")
    elif tarea == "prediccion":
        if (meses_historial or 0) >= 12 or etiquetados >= 500:
            rung = "ML_TABULAR"; camino.append(f"Datos en planilla con {'%d meses de historial' % meses_historial if (meses_historial or 0) >= 12 else '%d casos etiquetados' % etiquetados} -> ML clasico (Random Forest/Boosting), mas barato y explicable que un LLM")
        else:
            rung = "REGLAS"; camino.append("Menos de 12 meses de historial y menos de 500 casos etiquetados: empieza con reglas/umbrales y recolecta datos")
        if lenguaje or agente_atencion:
            comp += ["API_RAG", "VERIFICADOR"]; camino.append("Ademas responde en lenguaje natural -> API con RAG y verificador de citas y cifras")
    elif tarea == "asignacion":
        if recursos is not None and recursos <= 5:
            rung = "REGLAS"; camino.append(f"Solo {recursos} recursos: una planilla o regla simple basta")
        else:
            rung = "OPTIMIZACION"; camino.append("Asignar con restricciones -> funcion objetivo + solver/heuristica; el LLM solo formula o explica")
    else:  # accion
        if lenguaje or agente_atencion:
            rung = "API_RAG"; comp += ["REGLAS", "VERIFICADOR", "HUMANO"]
            camino.append("Responde y ademas ejecuta acciones con consecuencias -> API con RAG + reglas (limites y normativa) + verificador + humano que aprueba cada accion")
        elif pasos_variables:
            rung = "AGENTE"; camino.append("Acciones de varios pasos sobre sistemas reales -> agente con herramientas, con una persona que valide cada accion")
            comp.append("HUMANO")
        else:
            rung = "REGLAS"; camino.append("Accion de un solo paso con flujo fijo -> reglas/automatizacion clasica")
            comp.append("HUMANO")
    comp.insert(0, rung)
    if agente_atencion and rung == "API_RAG" and "VERIFICADOR" not in comp:
        comp.append("VERIFICADOR"); camino.append("Agente de atencion que responde con politicas o cifras -> verificador de citas y cifras")
    if regulado:
        comp += ["REGLAS", "VERIFICADOR", "HUMANO"]; camino.append("Normativa estricta -> reglas duras + verificador + humano en casos sensibles")
    comp = list(dict.fromkeys(comp))
    rungs = [c for c in comp if c in costs]
    rung = max(rungs, key=LADDER.index)                      # peldano tecnico mas alto de la arquitectura
    manual = volumen * costo_caso
    ahorro12 = 12 * manual * cobertura
    costo12 = sum(_tco(r, volumen, 12, costs) for r in rungs)
    paga = ahorro12 > costo12
    neto = manual * cobertura - sum(costs[r][1] + costs[r][2] * volumen for r in rungs)
    payback = round(sum(costs[r][0] for r in rungs) / neto, 1) if neto > 0 else None
    sobreventa = [{"alternativa": r, "sobrecosto_12m_usd": round(_tco(r, volumen, 12, costs) - costo12),
                   "por_que_no": WHY_NOT[r]} for r in LADDER[LADDER.index(rung) + 1:] if r in ("API_RAG", "SLM_PROPIO", "AGENTE", "ML_TABULAR")]
    verdict = rung if paga else "NO_AUTOMATIZAR_AUN"
    if not paga:
        camino.append(f"Con {volumen} casos/mes a ${costo_caso} y {int(cobertura*100)}% automatizable, ahorras ${ahorro12:,.0f}/12m y cuesta ${costo12:,.0f}: no se paga")
    return {"recomendacion": verdict, "peldano_tecnico": rung, "componentes": comp, "camino": camino,
            "costo_12m_usd": round(costo12), "ahorro_12m_usd": round(ahorro12), "se_paga_en_12m": paga,
            "payback_meses": payback, "sobreventa_evitada": [x for x in sobreventa if x["sobrecosto_12m_usd"] > 0],
            "supuestos": {"cobertura_automatizable": cobertura, "costos_(setup,fijo/mes,variable/caso)": {k: costs[k] for k in LADDER}},
            "aviso": "Costos = supuestos editables (config/advisor_costs.json); verifica precios y fecha en el Anexo B."}


def render(d):
    o = [f"## Recomendacion: {d['recomendacion']}", f"Componentes: {' + '.join(d['componentes'])}", "", "Como se llego (arbol de decision):"]
    o += [f"{i}. {c}" for i, c in enumerate(d["camino"], 1)]
    o += ["", f"Costo 12m: ${d['costo_12m_usd']:,} | Ahorro estimado 12m: ${d['ahorro_12m_usd']:,} | Se paga: {'si' if d['se_paga_en_12m'] else 'NO'} | Recupera inversion en: {d['payback_meses'] or 'n/a'} meses"]
    if d["sobreventa_evitada"]:
        o += ["", "Si te ofrecen algo mas caro, esto es lo que pagarias de mas (12m):"]
        o += [f"- {s['alternativa']}: +${s['sobrecosto_12m_usd']:,} -> {s['por_que_no']}" for s in d["sobreventa_evitada"]]
    return "\n".join(o + ["", "(" + d["aviso"] + ")"])


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    a = argparse.ArgumentParser(prog="copilot.advisor", description=__doc__.split("\n")[0])
    a.add_argument("--texto", help="describe tu negocio en texto libre (requiere --llm para convertirlo en datos)")
    a.add_argument("--tarea", choices=TAREAS)
    a.add_argument("--volumen", type=float, help="casos/consultas por mes")
    a.add_argument("--costo-caso", type=float, help="USD que cuesta hoy atender un caso a mano")
    a.add_argument("--etiquetados", type=int, default=0)
    a.add_argument("--preguntas-distintas", type=int)
    a.add_argument("--recursos", type=int, help="personas/vehiculos/maquinas a asignar")
    a.add_argument("--cobertura", type=float, default=0.7, help="fraccion automatizable (0-1)")
    a.add_argument("--meses-historial", type=int, help="meses de datos historicos en planilla (12 o mas ya permite ML clasico)")
    a.add_argument("--sin-personal-tecnico", action="store_true", help="no hay equipo tecnico: prefiere servicios administrados")
    for f in ("regulado", "privacidad", "herramienta-existente", "pasos-variables", "lenguaje", "agente-atencion"):
        a.add_argument("--" + f, action="store_true")
    a.add_argument("--llm", action="store_true", help="LLM (ChatGPT/Hugging Face del .env): extrae datos del texto y explica")
    a.add_argument("--json", action="store_true")
    ar = a.parse_args(argv)
    perfil = {k: v for k, v in vars(ar).items() if k in ("tarea", "volumen", "etiquetados", "preguntas_distintas", "recursos", "cobertura", "meses_historial")}
    perfil.update(personal_tecnico=False if ar.sin_personal_tecnico else None, agente_atencion=ar.agente_atencion)
    perfil.update(costo_caso=ar.costo_caso, regulado=ar.regulado, privacidad=ar.privacidad, herramienta_existente=ar.herramienta_existente,
                  pasos_variables=ar.pasos_variables, lenguaje=ar.lenguaje)
    if ar.texto:
        from .asesor_llm import extract_profile
        ext = extract_profile(ar.texto, use_llm=ar.llm)
        print("Datos entendidos del texto (revisalos; lo que pasaste por flags tiene prioridad):", json.dumps(ext, ensure_ascii=False))
        if ext.get("fuera_de_alcance"):
            print("Esa consulta no es de eleccion de una solucion de IA (pide un dato externo, un precio o una cita legal). No hay recomendacion que dar."); return
        for k, v in ext.items():
            if perfil.get(k) in (None, False, 0) and v not in (None, False):
                perfil[k] = v
    faltan = [k for k in ("tarea", "volumen", "costo_caso") if perfil.get(k) is None]
    if faltan:
        a.error("faltan datos: " + ", ".join(faltan) + " (pasalos por flags o agrega --texto con mas detalle)")
    d = decide(**profile_args(perfil))
    if ar.json:
        print(json.dumps(d, ensure_ascii=False, indent=2)); return
    print(render(d))
    if ar.llm:
        from .asesor_llm import explain
        try:
            print("\n## Explicacion para el usuario (LLM; la decision de arriba no cambia)\n" + explain(d, perfil))
        except Exception as e:
            print(f"\n! No se pudo generar la explicacion con LLM: {e}\n  La recomendacion de arriba sigue siendo valida.")


if __name__ == "__main__":
    main()
