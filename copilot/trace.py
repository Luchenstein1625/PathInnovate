"""Pasos 5-6 y 10: tabla de trazabilidad (anexo A) y chequeo de cobertura de un borrador."""

import csv
import re
from collections import Counter
from pathlib import Path

from . import defaults as D
from .extract import extract, read_text
from .index import cite
from .textutil import norm

TOPIC_FIELDS = ["sesion", "id", "topico", "palabras_clave", "secciones"]


def write_topics(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(TOPIC_FIELDS)
        w.writerows(D.TOPICS)


def load_topics(path):
    path = Path(path)
    if not path.exists():
        return [dict(zip(TOPIC_FIELDS, t)) for t in D.TOPICS]
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def keywords(topic):
    return [k.strip() for k in topic["palabras_clave"].split(";") if k.strip()]


def matched(text, kws):
    nt = f" {norm(text)} "
    return [k for k in kws if f" {norm(k)} " in nt]


def _occurrences(text, kws):
    nt = f" {norm(text)} "
    return sum(nt.count(f" {norm(k)} ") for k in kws)


def evidence(idx, kws, courses=None, session=None, k=3):
    """Trozos donde aparece alguna frase clave completa, los fuertes primero.

    Un trozo es "fuerte" si contiene al menos 2 frases clave distintas o 3 apariciones: una sola palabra suelta
    (por ejemplo "token" o "riesgo") aparece en casi cualquier clase y no demuestra que el tópico se dictó.
    """
    out = []
    for h in idx.search(" ".join(kws), k=150, course=courses, session=session):
        m = matched(h["text"], kws)
        if not m:
            continue
        strong = len(m) >= 2 or _occurrences(h["text"], kws) >= 3
        out.append((strong, len(m), h["score"], h, m))
    out.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
    return out[:k]


def _fmt(ev):
    return " | ".join(f"{cite(h)}{'' if strong else ' (débil)'}" for strong, _, _, h, _ in ev)


def _has_strong(ev):
    return any(e[0] for e in ev)


def trace(idx, topics):
    recorded = set(idx.sessions())
    rows = []
    for t in topics:
        kws = keywords(t)
        sess = t["sesion"]
        has_rec = sess in recorded
        ev_own = evidence(idx, kws, session=sess, courses={D.TAAI2}) if has_rec else []
        ev16 = evidence(idx, kws, courses={D.TAAI2})
        ev_sup = evidence(idx, kws, courses=set(D.SUPPORT.get(sess, [])))
        if sess == "T":  # transversal: cualquier sesión TAAI2 vale
            ev_own, has_rec = ev16, bool(recorded)
        if has_rec and _has_strong(ev_own):
            estado = "transversal en TAAI2" if sess == "T" else f"dictado en {sess}"
        elif sess in D.TAAI2_ALL_SESSIONS and not has_rec:
            estado = "SESIÓN SIN GRABACIÓN"
        elif _has_strong(ev16):
            estado = "visto en otra sesión TAAI2"
        elif has_rec and ev_own:
            estado = f"mención débil en {sess}" if sess != "T" else "mención débil en TAAI2"
        elif _has_strong(ev_sup):
            estado = "solo cursos de apoyo"
        elif ev16 or ev_sup:
            estado = "mención débil (otros cursos)"
        else:
            estado = "SIN MATERIAL"
        rows.append({
            "sesion": sess, "id": t["id"], "topico": t["topico"], "secciones_informe": t["secciones"],
            "estado_material": estado,
            "evidencia_sesion_propia": _fmt(ev_own) if sess != "T" else "",
            "evidencia_TAAI2": _fmt(ev16),
            "evidencia_apoyo": _fmt(ev_sup),
            "aplicado_en_informe": "", "pagina_informe": "", "justificacion_si_no_aplica": "",
        })
    return rows


GOOD = ("dictado en", "transversal")


def write_trace(rows, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "trazabilidad_borrador.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    def first(cell):
        parts = [p for p in cell.split(" | ") if p]
        return (parts[0] + (f" (+{len(parts) - 1})" if len(parts) > 1 else "")) if parts else "-"

    lines = ["# Anexo A (borrador): trazabilidad del syllabus", "",
             "| Sesión | Tópico | Sec. informe | Material | Mejor evidencia |", "|---|---|---|---|---|"]
    for r in rows:
        ev = r["evidencia_sesion_propia"] or r["evidencia_TAAI2"] or r["evidencia_apoyo"]
        lines.append(f"| {r['sesion']} | {r['topico']} | {r['secciones_informe']} | {r['estado_material']} | {first(ev)} |")
    lines += ["", "Las columnas de aplicación (sección y página del informe, justificación) se completan a mano "
              "en el CSV una vez escrito el informe."]
    (out_dir / "trazabilidad_borrador.md").write_text("\n".join(lines), encoding="utf-8")
    return Counter(r["estado_material"] for r in rows)


# ---------------------------------------------------------------- chequeo de borrador

SECTION_PATTERNS = [
    ("0", "resumen ejecutivo"), ("1", "la solucion"), ("2", "modelos fundacionales"), ("3", "autonomia"),
    ("4", "simbolico"), ("5", "planificacion"), ("6", "optimizacion"), ("7", "despliegue"),
    ("8", "presupuesto"), ("9", "factibilidad"), ("10", "estrategia"), ("11", "plan de evaluacion"),
    ("12", "recomendacion"), ("A", "trazabilidad"), ("B", "supuestos"), ("C", "uso de ia"), ("D", "aportes"),
]


def _draft_text(path):
    path = Path(path)
    if path.suffix.lower() in (".md", ".txt"):
        return read_text(path)
    units, _ = extract(path)
    return "\n".join(t for _, t in units)


def _blocks(text):
    """Divide el borrador por encabezados markdown y asigna cada bloque a una sección del informe."""
    blocks, cur, body = {}, None, []
    headings = []
    for line in text.splitlines():
        h = re.match(r"^#{1,6}\s+(.*)", line)
        if h:
            if cur is not None:
                blocks[cur] = blocks.get(cur, "") + "\n".join(body) + "\n"
            title = norm(h.group(1))
            headings.append(title)
            cur = next((sid for sid, pat in SECTION_PATTERNS if pat in title), None)
            body = []
        else:
            body.append(line)
    if cur is not None:
        blocks[cur] = blocks.get(cur, "") + "\n".join(body) + "\n"
    return blocks, headings


def check(draft_path, topics):
    text = _draft_text(draft_path)
    blocks, headings = _blocks(text)
    words = len(text.split())
    found = {sid for sid in blocks}
    missing = [f"{sid} ({pat})" for sid, pat in SECTION_PATTERNS
               if sid not in found and not (not headings and pat in norm(text))]
    rows = []
    for t in topics:
        kws = keywords(t)
        occ = Counter()
        nt = f" {norm(text)} "
        for k in kws:
            c = nt.count(f" {norm(k)} ")
            if c:
                occ[k] = c
        total, distinct = sum(occ.values()), len(occ)
        secs = [s.strip() for s in t["secciones"].split(";") if s.strip()]
        in_sec = 0
        if blocks:
            for s in secs:
                nb = f" {norm(blocks.get(s, ''))} "
                in_sec += sum(nb.count(f" {norm(k)} ") for k in kws)
        if total == 0:
            estado = "AUSENTE"
        elif blocks and in_sec == 0:
            estado = "MENCIONADO FUERA DE SU SECCIÓN"
        elif total < 3 or distinct < 2:
            estado = "SOLO MENCIONADO (revisar)"
        else:
            estado = "desarrollado (revisar a mano)"
        rows.append({"id": t["id"], "topico": t["topico"], "secciones": t["secciones"], "ocurrencias": total,
                     "frases_distintas": distinct, "en_su_seccion": in_sec, "estado": estado})
    return {"palabras": words, "paginas_aprox": round(words / 450, 1), "secciones_faltantes": missing,
            "tiene_encabezados": bool(headings), "topicos": rows}


def render_check(res):
    lines = ["# Chequeo de cobertura del borrador (heurístico)", "",
             f"- Palabras: {res['palabras']} (≈ {res['paginas_aprox']} páginas a 11 pt, estimación gruesa; "
             "el enunciado pide 20 a 35 sin anexos)"]
    if not res["tiene_encabezados"]:
        lines.append("- El borrador no tiene encabezados markdown (#): no se pudo verificar en qué sección está cada tópico.")
    lines.append("- Secciones/anexos no encontrados: " + (", ".join(res["secciones_faltantes"]) or "ninguno"))
    lines += ["", "| Tópico | Sec. | Ocurrencias | En su sección | Estado |", "|---|---|---|---|---|"]
    for r in res["topicos"]:
        lines.append(f"| {r['id']} {r['topico']} | {r['secciones']} | {r['ocurrencias']} | {r['en_su_seccion']} | {r['estado']} |")
    lines += ["", "Este chequeo cuenta frases clave: no entiende si un tópico está bien aplicado a la solución. "
              "Úsalo para encontrar vacíos, no como evidencia de calidad."]
    return "\n".join(lines)
