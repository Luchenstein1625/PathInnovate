"""Evaluación en el dominio de PathInnovate (asesoría para emprendedores).
Uso:  python run_eval_asesor.py [--repeats 3] [--skip-local] [--preguntas RUTA.json] [--salida CARPETA]
Por defecto usa eval_asesor/preguntas.json y escribe en eval_asesor/. Con --preguntas/--salida se puede evaluar otro
conjunto (p. ej. preguntas externas) sin tocar los resultados anteriores. El corpus siempre es eval_asesor/corpus.json."""
import argparse, json
from pathlib import Path
from copilot.evaluator_asesor import ROOT, run_benchmark_asesor

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--repeats", type=int, default=1); ap.add_argument("--skip-local", action="store_true")
    ap.add_argument("--preguntas", help="JSON de preguntas (por defecto eval_asesor/preguntas.json)")
    ap.add_argument("--salida", help="carpeta de salida (por defecto eval_asesor/)")
    ar = ap.parse_args()
    from copilot.llm import load_env; load_env()
    from copilot.llm_dual import DualLLMRunner
    src = ROOT / "eval_asesor"
    d = Path(ar.salida) if ar.salida else src
    d.mkdir(parents=True, exist_ok=True)
    runner = DualLLMRunner(load_local=not ar.skip_local)
    qpath = Path(ar.preguntas) if ar.preguntas else src / "preguntas.json"
    pre, cor = json.loads(qpath.read_text(encoding="utf-8")), json.loads((src / "corpus.json").read_text(encoding="utf-8"))
    res = run_benchmark_asesor(runner, pre, cor, ar.repeats, not ar.skip_local)
    res["meta"]["archivo_preguntas"] = str(qpath)
    out = d / "resultados_asesor.json"; out.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        from run_eval import attach_extras
        res = attach_extras(res, runner, d); out.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print("Extras de presupuesto no generados:", e)
    (d / "resultados_asesor.js").write_text("window.RESULTADOS_ASESOR = " + json.dumps(res, ensure_ascii=False, indent=2) + ";\n", encoding="utf-8")
    print("preguntas:", qpath, "| recall de la regla correcta en top-k:", res["meta"]["recall_regla_correcta_en_top_k"])
    for c, v in res["configs"].items():
        m = v["metricas"]
        print(c, {k: m.get(k) for k in ("n", "correctas", "sobredimensionadas", "subdimensionadas", "inventa_fuera_de_corpus", "sin_cita", "alucinacion", "abstenciones", "parcial_compuestas", "latencia_p50_s", "latencia_p95_s", "costo_medio_usd", "tokens_in_medios", "reparadas", "reintentos")})
    print("Escrito:", out, "| Errores:", len(res["errores"]))
