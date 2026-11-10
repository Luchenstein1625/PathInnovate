"""Interfaz web local del asesor: python -m copilot.web [--port 8000]. Solo escucha en 127.0.0.1 (tus claves nunca salen del PC).
La decision la toma advisor.decide(); el LLM (opcional) solo entiende el texto y explica."""
import argparse, json, sys, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .advisor import TAREAS, decide, profile_args

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / "index.html"   # pagina unica: pestanas Asesor + Benchmark
STATIC = {"/resultados.js": "resultados.js", "/eval_asesor/resultados_asesor.js": "eval_asesor/resultados_asesor.js"}
NUM = ("volumen", "costo_caso", "cobertura")
INT = ("etiquetados", "preguntas_distintas", "recursos", "meses_historial")
BOOL = ("regulado", "privacidad", "herramienta_existente", "pasos_variables", "lenguaje", "agente_atencion")


def clean(d: dict) -> dict:
    out = {}
    for k in NUM:
        if d.get(k) not in (None, ""): out[k] = float(d[k])
    for k in INT:
        if d.get(k) not in (None, ""): out[k] = int(float(d[k]))
    for k in BOOL: out[k] = bool(d.get(k))
    if d.get("sin_personal_tecnico"): out["personal_tecnico"] = False
    if d.get("tarea") in TAREAS: out["tarea"] = d["tarea"]
    return out


def handle(body: dict) -> dict:
    perfil, res = clean(body), {}
    texto = (body.get("texto") or "").strip()
    usar_llm = bool(body.get("llm"))
    if texto:
        from .asesor_llm import extract_profile
        ext = extract_profile(texto, use_llm=usar_llm)
        res["entendido_del_texto"] = ext
        if ext.get("fuera_de_alcance"):
            return {**res, "error": "Esa consulta no es de eleccion de una solucion de IA (pide un dato externo, un precio o una cita legal)."}
        for k, v in ext.items():          # lo que escribio el usuario en el formulario tiene prioridad
            if perfil.get(k) in (None, False) and v not in (None, False): perfil[k] = v
    perfil.setdefault("cobertura", 0.7)
    falta = [k for k in ("tarea", "volumen", "costo_caso") if perfil.get(k) is None]
    if falta:
        return {**res, "error": "Faltan datos: " + ", ".join(falta)}
    d = decide(**profile_args(perfil)); res.update(decision=d, perfil=perfil)
    if usar_llm:
        try:
            from .asesor_llm import explain
            res["explicacion"] = explain(d, perfil)
        except Exception as e:
            res["explicacion_error"] = str(e)
    return res


class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype):
        b = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        if self.path in ("/", "/index.html", "/asesor.html"):
            self._send(200, HTML.read_bytes(), "text/html; charset=utf-8")
        elif self.path in STATIC and (ROOT / STATIC[self.path]).exists():
            self._send(200, (ROOT / STATIC[self.path]).read_bytes(), "application/javascript; charset=utf-8")
        elif self.path in STATIC:   # sin resultados todavia: el panel avisa que muestra ejemplos
            self._send(200, "", "application/javascript; charset=utf-8")
        else:
            self._send(404, "no encontrado", "text/plain; charset=utf-8")

    def do_POST(self):
        if self.path != "/api/decide":
            return self._send(404, "no encontrado", "text/plain; charset=utf-8")
        try:
            n = min(int(self.headers.get("Content-Length", 0)), 50_000)
            out = handle(json.loads(self.rfile.read(n) or b"{}"))
        except Exception as e:
            out = {"error": f"Entrada invalida: {e}"}
        self._send(200, json.dumps(out, ensure_ascii=False), "application/json; charset=utf-8")

    def log_message(self, *a):
        pass


def main(argv=None):
    ap = argparse.ArgumentParser(prog="copilot.web"); ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args(argv)
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), H)
    url = f"http://127.0.0.1:{a.port}/"
    print(f"Asesor PathInnovate en {url}  (Ctrl+C para cerrar)")
    if not a.no_browser: webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nCerrado.")


if __name__ == "__main__":
    main()
