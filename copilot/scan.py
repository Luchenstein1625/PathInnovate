"""Paso 1: recorre la carpeta del magíster y arma un inventario clasificado (inventory.csv)."""

import csv
import os
import re
from collections import Counter, defaultdict
from pathlib import Path

from . import defaults as D
from .extract import extract
from .textutil import norm, tokenize

SUPPORTED = {".txt", ".vtt", ".srt", ".tsv", ".md", ".pdf", ".pptx", ".docx", ".ipynb"}
PRUNE = {".git", "node_modules", "__pycache__", ".ipynb_checkpoints", ".venv"}
# Subcarpetas de "Otros" sin relación con el syllabus (se comparan contra el nombre normalizado,
# sin letras con tilde para que no importe cómo quedó codificado el nombre).
OTROS_EXCLUDE = ("python", "agent ai", "diplomado", "certificaciones")
SKIP_STEMS = {"estructura completa", "readme"}
EVAL_WORDS = ("rubrica", "pauta", "enunciado", "temario", "guia tarea", "guia de tarea")
# Con tiempo primero: así las citas pueden indicar el minuto de la clase.
TRANSCRIPT_PREF = {".vtt": 0, ".srt": 1, ".tsv": 2, ".txt": 3}
TRANSCRIPT_EXT = set(TRANSCRIPT_PREF)
DUP_THRESHOLD = 0.25  # similitud (trigramas en común / el mayor de los dos) desde la cual son la misma clase
FIELDS = ["rel", "course", "course_name", "kind", "ext", "size_kb", "fecha", "session", "status", "note"]
DATE_RE = (re.compile(r"(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)"), re.compile(r"GMT(\d{4})(\d{2})(\d{2})"))


def date_of(name):
    for rx in DATE_RE:
        m = rx.search(name)
        if m:
            return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return ""


def course_of(rel_parts, stem_norm):
    if not rel_parts:
        base = re.sub(r"^\d+\s*", "", stem_norm)
        return D.ROOT_MD.get(base, "ROOT")
    m = re.match(r"\s*(\d{2})\b", rel_parts[0])
    if m:
        return m.group(1)
    if norm(rel_parts[0]) == "otros":
        return "OTROS"
    return "ROOT"


def kind_of(rel_parts, stem_norm, ext):
    root_level = not rel_parts
    in_books = any("libros" in norm(p) or "papers" in norm(p) for p in rel_parts)
    if root_level and ext == ".md":
        return "meta" if stem_norm == "readme" else "resumen"
    if stem_norm in SKIP_STEMS or stem_norm.startswith("transcription log"):
        return "meta"
    if "syllabus" in stem_norm:
        return "syllabus"
    if any(w in stem_norm for w in EVAL_WORDS):
        return "evaluacion"
    if ext in (".srt", ".vtt", ".tsv"):
        return "transcript"
    if ext == ".txt":
        if "chat" in stem_norm:
            return "chat"
        if in_books:
            return "libro"
        if stem_norm == "links":
            return "otro"
        return "transcript"
    if ext == ".pptx":
        return "slides"
    if ext == ".ipynb":
        return "notebook"
    if in_books:
        return "libro"
    if "resumen" in stem_norm:
        return "resumen"
    return "material"


def excluded_dir(rel_parts, include_otros, include_capstone):
    """Devuelve el motivo si la carpeta debe saltarse, o None."""
    if not rel_parts or norm(rel_parts[0]) != "otros" or len(rel_parts) < 2:
        return None
    n = norm(rel_parts[-1])
    if not include_otros and (any(k in n for k in OTROS_EXCLUDE) or n == "web"):
        return "sin relación con el syllabus (usa --include-otros para incluirla)"
    if not include_capstone and "capstone" in n:
        return "material de proyecto bancario: confidencial (usa --include-capstone para incluirla)"
    return None


def _recording_key(path):
    stem = os.path.splitext(os.path.basename(path))[0]
    stem = re.sub(r"\.cc$", "", stem, flags=re.I)
    stem = re.sub(r"[ _]?\d{3,4}x\d{3,4}$", "", stem)
    return (os.path.dirname(path), stem.lower())


def scan(root, include_otros=False, include_capstone=False, max_mb=15, content_dedupe=True):
    root = Path(root)
    if not root.is_dir():
        raise SystemExit(f"No existe la carpeta: {root}")
    rows = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = Path(dirpath).relative_to(root)
        parts = list(rel_dir.parts)
        keep = []
        for d in sorted(dirnames):
            if d in PRUNE:
                continue
            reason = excluded_dir(parts + [d], include_otros, include_capstone)
            if reason:
                rows.append(_row("/".join(parts + [d]) + "/", "OTROS", "dir", "", 0, "excluido", reason))
            else:
                keep.append(d)
        dirnames[:] = keep
        for fn in sorted(filenames):
            full = Path(dirpath) / fn
            stem, ext = os.path.splitext(fn)
            ext = ext.lower()
            sn = norm(stem)
            kind = kind_of(parts, sn, ext)
            course = course_of(parts, sn)
            size = full.stat().st_size
            if kind == "meta":
                status, note = "meta", ""
            elif ext not in SUPPORTED:
                status, note = "sin_soporte", ""
            elif size > max_mb * 1024 * 1024:
                status, note = "muy_grande", f">{max_mb} MB"
            else:
                status, note = "indexar", ""
            fecha = date_of(fn)
            session = D.TAAI2_SESSIONS.get(fecha, "") if course == D.TAAI2 else ""
            rows.append(_row("/".join(parts + [fn]), course, kind, ext, size, status, note, fecha, session))
    if content_dedupe:
        _dedupe_by_content(rows, root)
    else:
        _dedupe_transcripts(rows)
    return rows


def _row(rel, course, kind, ext, size, status, note, fecha="", session=""):
    return {
        "rel": rel, "course": course, "course_name": D.COURSES.get(course, course), "kind": kind,
        "ext": ext, "size_kb": round(size / 1024, 1), "fecha": fecha, "session": session,
        "status": status, "note": note,
    }


def _dedupe_transcripts(rows):
    """Mismo nombre base en la misma carpeta (.txt/.srt/.vtt/.tsv): deja el que trae tiempo."""
    groups = defaultdict(list)
    for r in rows:
        if r["kind"] == "transcript" and r["status"] == "indexar":
            groups[_recording_key(r["rel"])].append(r)
    for g in groups.values():
        if len(g) > 1:
            g.sort(key=lambda r: TRANSCRIPT_PREF.get(r["ext"], 9))
            for r in g[1:]:
                r["status"], r["note"] = "duplicado", f"misma grabación que {os.path.basename(g[0]['rel'])}"


def _fingerprint(root, rel):
    units, _ = extract(Path(root) / rel, "transcript")
    toks = tokenize(" ".join(t for _, t in units))
    return len(toks), {hash(tuple(toks[i : i + 3])) for i in range(len(toks) - 2)}


def _dedupe_by_content(rows, root):
    """Detecta la misma clase guardada en varios formatos, con otro nombre o en otra carpeta.

    Compara, dentro de cada curso, los trigramas de palabras en común entre todas las transcripciones
    (una misma clase puede venir como .vtt, .srt, .txt, .tsv y como copia en una subcarpeta). También une los
    archivos con el mismo nombre base en una carpeta, porque dos transcripciones automáticas de una misma clase
    pueden diferir en el texto. En el material real
    las copias caen sobre 0,29 y las clases distintas bajo 0,03, por lo que el umbral de 0,25 las separa.
    Se divide por el archivo más largo para que una clase corta no se confunda con una larga que la contiene.
    De cada grupo se conserva una versión: con tiempo (.vtt, .srt, .tsv, .txt en ese orden) y, a igualdad, la más larga.
    """
    by_course = defaultdict(list)
    for r in rows:
        if r["kind"] == "transcript" and r["status"] == "indexar" and r["ext"] in TRANSCRIPT_EXT:
            by_course[r["course"]].append(r)
    for course_rows in by_course.values():
        if len(course_rows) < 2:
            continue
        fp = {}
        for r in course_rows:
            try:
                fp[r["rel"]] = _fingerprint(root, r["rel"])
            except Exception:
                fp[r["rel"]] = (0, set())
        parent = {r["rel"]: r["rel"] for r in course_rows}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        same_name = {}
        for r in course_rows:  # misma carpeta y mismo nombre base (.vtt, .cc.vtt, .srt, .txt): misma grabación
            first = same_name.setdefault(_recording_key(r["rel"]), r["rel"])
            if first != r["rel"]:
                parent[find(r["rel"])] = find(first)
        for i, a in enumerate(course_rows):
            for b in course_rows[i + 1 :]:
                sa, sb = fp[a["rel"]][1], fp[b["rel"]][1]
                if sa and sb and len(sa & sb) / max(len(sa), len(sb)) >= DUP_THRESHOLD:
                    parent[find(a["rel"])] = find(b["rel"])
        clusters = defaultdict(list)
        for r in course_rows:
            clusters[find(r["rel"])].append(r)
        for cl in clusters.values():
            if len(cl) > 1:
                cl.sort(key=lambda r: (TRANSCRIPT_PREF.get(r["ext"], 9), -fp[r["rel"]][0], len(r["rel"])))
                for r in cl[1:]:
                    r["status"], r["note"] = "duplicado", f"mismo contenido que {cl[0]['rel']}"


def write_inventory(rows, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def read_inventory(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    for r in rows:  # inventarios de versiones anteriores no traen estas columnas
        r.setdefault("fecha", "")
        r.setdefault("session", "")
    return rows


def taai2_sessions(rows):
    """{sesión: [fechas]} de las grabaciones TAAI2 que se van a indexar."""
    out = defaultdict(set)
    for r in rows:
        if r["course"] == D.TAAI2 and r["status"] == "indexar" and r["kind"] == "transcript" and r.get("session"):
            out[r["session"]].add(r["fecha"])
    return {k: sorted(v) for k, v in out.items()}


def summary(rows):
    """Texto con el resumen por curso y alertas sobre material faltante."""
    per = defaultdict(Counter)
    for r in rows:
        if r["kind"] == "dir" or r["status"] == "meta":
            continue
        c = per[r["course"]]
        c["archivos"] += 1
        if r["status"] == "indexar":
            c["indexar"] += 1
            c[r["kind"]] += 1
        elif r["status"] == "duplicado":
            c["dup"] += 1
    lines = [f"{'curso':<9}{'archivos':>9}{'indexar':>9}{'dup.':>6}  transcript/chat/slides/material",
             "-" * 74]
    for key in sorted(per, key=lambda k: (not k.isdigit(), k)):
        c = per[key]
        lines.append(f"{key:<9}{c['archivos']:>9}{c['indexar']:>9}{c['dup']:>6}  "
                     f"{c['transcript']}/{c['chat']}/{c['slides']}/{c['material']}  {D.COURSES.get(key, '')}")
    excl = [r for r in rows if r["kind"] == "dir"]
    if excl:
        lines += ["", "Carpetas excluidas:"] + [f"  - {r['rel']}  ({r['note']})" for r in excl]
    lines += ["", "Alertas:"]
    have = taai2_sessions(rows)
    miss = [s for s in D.TAAI2_ALL_SESSIONS if s not in have]
    lines.append("  - TAAI2 con grabación: " + (", ".join(f"{s} ({'/'.join(have[s])})" for s in sorted(have)) or "ninguna"))
    if miss:
        lines.append("  - TAAI2 sin grabación indexada: " + ", ".join(miss)
                     + ". Sus tópicos saldrán como 'SESIÓN SIN GRABACIÓN' en `trace`.")
    t = per.get(D.TAAI2, Counter())
    if not t["slides"] and not t["material"] and not t["syllabus"]:
        lines.append("  - TAAI2 (16): solo hay transcripciones; no se encontraron diapositivas, PDFs ni el syllabus. "
                     "Los tópicos de config/topics.csv no se pueden contrastar con el syllabus oficial.")
    big = [r for r in rows if r["status"] == "muy_grande"]
    if big:
        lines.append(f"  - {len(big)} archivo(s) superan el límite de tamaño (status=muy_grande).")
    unsup = Counter(r["ext"] for r in rows if r["status"] == "sin_soporte")
    if unsup:
        lines.append("  - Sin soporte (se ignoran): " + ", ".join(f"{e or '(sin ext)'}×{n}" for e, n in unsup.most_common(8)))
    return "\n".join(lines)
