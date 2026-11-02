"""Ejecuta el benchmark real y regenera eval/resultados.json + resultados.js (los lee index.html).
Uso:  python run_eval.py [--repeats 3] [--skip-local]"""
import argparse
from copilot import budget_extras as bx
from copilot.engine_taai2 import Assumptions
from copilot.evaluator import ROOT, load_eval, run_benchmark, write_outputs
from copilot.optimizer import WorkloadOptimizer

TAREAS = [{"id": "T1", "name": "Redacción sección 1", "duration_hours": 4.0, "depends_on": []},
          {"id": "T2", "name": "Presupuesto y TCO", "duration_hours": 6.0, "depends_on": ["T1"]},
          {"id": "T3", "name": "Revisión final", "duration_hours": 2.0, "depends_on": ["T2"]},
          {"id": "T4", "name": "Riesgos", "duration_hours": 5.0, "depends_on": []},
          {"id": "T5", "name": "Plan de evaluación", "duration_hours": 3.0, "depends_on": ["T4"]}]
MIEMBROS = {"Integrante_1": 14.0, "Integrante_2": 14.0, "Integrante_3": 14.0}


def attach_extras(res, runner=None, root=ROOT):
    o = WorkloadOptimizer(MIEMBROS); s = o.schedule(TAREAS); ex = o.exact(TAREAS)
    res["optimizador"] = {"metodo": "despacho por camino crítico (heurístico)", "makespan_horas": s["makespan_hours"],
                          "max_carga_horas": s["balanced_metric_makespan"], "cota_camino_critico": s["critical_path_hours"],
                          "optimo_exacto_horas": ex["makespan_hours"], "asignacion": s["assignment"], "sin_asignar": len(s["unassigned_tasks"])}
    m = res["configs"].get("rag_openai", {}).get("metricas", {})
    ml = res["configs"].get("rag_local", {}).get("metricas", {})
    if m.get("n"):
        rates = getattr(runner, "rates", {"openai": {"input": 0.15e-6, "output": 0.60e-6}})["openai"]
        a = bx.from_measurements(Assumptions(), m["tokens_in_medios"], m["tokens_out_medios"], ml.get("latencia_p50_s", 1.0) if ml.get("n") else 1.0,
                                 rates["input"] * 1e6, rates["output"] * 1e6)
        res["tco"] = bx.tco_for_dashboard(a, 12)
        res["tco"]["fuente"] = "Tokens, precios y latencia tomados de esta corrida; el resto son supuestos (ver Anexo B)."
        try:
            bx.export_anexo_b(a, str(root / "Anexo_B.xlsx"), fecha_corrida=res["meta"]["fecha"],
                              medidos={"prompt_tokens": "rag_openai tokens_in_medios", "completion_tokens": "rag_openai tokens_out_medios",
                                       "gpu_hours_month": "consultas x latencia p50 local / utilización 30 %"},
                              verificados={"api_in_per_mtok": ("https://developers.openai.com/api/docs/pricing", "2026-11-01"),
                                           "api_out_per_mtok": ("https://developers.openai.com/api/docs/pricing", "2026-11-01")})
        except Exception as e:  # no perder la corrida por un fallo del Excel
            print("Anexo_B.xlsx no generado:", e)
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--repeats", type=int, default=1); ap.add_argument("--skip-local", action="store_true")
    ar = ap.parse_args()
    from copilot.llm import load_env; load_env()
    from copilot.llm_dual import DualLLMRunner
    runner = DualLLMRunner(load_local=not ar.skip_local)
    preguntas, corpus = load_eval()
    res = run_benchmark(runner, preguntas, corpus, ar.repeats, not ar.skip_local)
    write_outputs(res)  # guarda lo medido antes de cualquier cálculo extra
    res = attach_extras(res, runner)
    write_outputs(res)
    for c, v in res["configs"].items():
        print(c, v["metricas"])
    print("Escrito: eval/resultados.json, resultados.js, Anexo_B.xlsx. Errores:", len(res["errores"]))
