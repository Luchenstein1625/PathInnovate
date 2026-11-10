"""Agrega la configuracion 'motor_reglas' a un benchmark del asesor YA medido, sin repetir las otras 5 (no gasta mas API en ellas).
Uso:  python run_eval_motor.py                       # usa OpenAI (gpt-4o-mini) como extractor; necesita OPENAI_API_KEY
      python run_eval_motor.py --sin-llm              # solo palabras clave (costo 0; extractor pobre, sirve de piso)
      python run_eval_motor.py --preguntas eval_asesor/preguntas_externas.json --base eval_asesor/externas/resultados_asesor.json
Lee <base> (.json, o .js si no hay .json), agrega la config y reescribe .json y .js junto al original."""
import argparse, json
from pathlib import Path
from copilot.llm import load_env
from copilot.motor_asesor import add_config

ROOT = Path(__file__).resolve().parent


def load(base: Path):
    if base.exists():
        return json.loads(base.read_text(encoding="utf-8"))
    js = base.with_suffix(".js")
    if js.exists():
        t = js.read_text(encoding="utf-8")
        return json.loads(t[t.index("=") + 1:].strip().rstrip(";"))
    raise SystemExit(f"No encuentro {base} ni {js}. Corre antes: python run_eval_asesor.py")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=str(ROOT / "eval_asesor" / "resultados_asesor.json"))
    ap.add_argument("--preguntas", default=str(ROOT / "eval_asesor" / "preguntas.json"))
    ap.add_argument("--sin-llm", action="store_true")
    ar = ap.parse_args()
    load_env()
    base = Path(ar.base)
    res = load(base)
    preg = json.loads(Path(ar.preguntas).read_text(encoding="utf-8"))
    ids = {p["id"] for p in res["preguntas"]}
    preg = [p for p in preg if p["id"] in ids]
    if not preg:
        raise SystemExit("Las preguntas no coinciden con las del resultado base (usa el mismo --preguntas con el que se midio).")
    runner = None
    if not ar.sin_llm:
        from copilot.llm_dual import DualLLMRunner
        runner = DualLLMRunner(load_local=False)
    res = add_config(res, preg, runner)
    base.parent.mkdir(parents=True, exist_ok=True)
    base.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    base.with_suffix(".js").write_text("window.RESULTADOS_ASESOR = " + json.dumps(res, ensure_ascii=False, indent=2) + ";\n", encoding="utf-8")
    m = res["configs"]["motor_reglas"]["metricas"]
    print({k: m.get(k) for k in ("n", "correctas", "sobredimensionadas", "subdimensionadas", "abstenciones", "inventa_fuera_de_corpus", "parcial_compuestas", "latencia_p50_s", "costo_medio_usd")})
    print("Escrito:", base, "y", base.with_suffix(".js"))
