"""Temario por clase: términos distintivos por ventana de tiempo, para recordar qué se vio y cuándo."""

import math
import re
from collections import Counter, defaultdict

from . import defaults as D
from .textutil import FILLER, tokenize

MIN_UNI, MIN_BI = 4, 3  # apariciones mínimas dentro de una ventana


def _start(loc):
    """(segundos, None) para citas con hora; (None, porcentaje) para citas posicionales (≈12%)."""
    first = loc.split("–")[0]
    m = re.match(r"(\d+):(\d{2}):(\d{2})", first)
    if m:
        return int(m[1]) * 3600 + int(m[2]) * 60 + int(m[3]), None
    m = re.match(r"≈(\d+)%", first)
    return (None, int(m[1])) if m else (None, None)


def _grams(text):
    toks = [t for t in tokenize(text) if t not in FILLER and not t.isdigit()]
    return toks + [f"{a} {b}" for a, b in zip(toks, toks[1:])]


def _hm(seconds):
    return f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}"


def outline(idx, courses, window_min=15, top=8):
    """Devuelve un texto markdown con el temario de las transcripciones de los cursos indicados."""
    wanted = set(courses)
    files = defaultdict(lambda: defaultdict(Counter))  # archivo -> ventana -> términos
    meta = {}
    for c in idx.chunks:
        if c["course"] not in wanted or c["kind"] != "transcript":
            continue
        sec, pct = _start(c["loc"])
        if sec is not None:
            win = ("t", sec // (window_min * 60))
        elif pct is not None:
            win = ("p", pct // 10)
        else:
            continue
        files[c["file"]][win].update(_grams(c["text"]))
        meta[c["file"]] = (c.get("fecha", ""), c.get("session", ""), c["course"], c["course_name"])
    if not files:
        return "No hay transcripciones indexadas para ese curso."
    df = Counter()
    n_win = 0
    for wins in files.values():
        for terms in wins.values():
            n_win += 1
            df.update(terms.keys())
    lines = []
    last_course = None
    for fname in sorted(files, key=lambda f: (meta[f][2], meta[f][0], f)):
        fecha, session, course, cname = meta[fname]
        if course != last_course:
            lines += [f"# Temario · {course} {cname}", ""]
            last_course = course
        tag = " · ".join(x for x in (session, fecha) if x)
        lines.append(f"## {tag + ' · ' if tag else ''}{fname.split('/')[-1]}")
        for win in sorted(files[fname]):
            terms = files[fname][win]
            scored = []
            for g, n in terms.items():
                if n < (MIN_BI if " " in g else MIN_UNI):
                    continue
                scored.append((n * math.log(1 + n_win / df[g]) * (1.4 if " " in g else 1.0), g))
            scored.sort(reverse=True)
            chosen = []
            for _, g in scored:
                if len(chosen) >= top:
                    break
                if " " not in g and any(g in b.split() for b in chosen):
                    continue  # la palabra ya aparece dentro de un bigrama elegido
                if " " in g and any(set(g.split()) <= set(b.split()) for b in chosen if " " in b):
                    continue
                chosen.append(g)
            if win[0] == "t":
                label = f"{_hm(win[1] * window_min * 60)}–{_hm((win[1] + 1) * window_min * 60)}"
            else:
                label = f"≈{win[1] * 10}–{win[1] * 10 + 10}%"
            lines.append(f"- {label} · " + (", ".join(chosen) if chosen else "(sin términos distintivos)"))
        lines.append("")
    lines.append("Los términos salen de contar palabras y pares de palabras que se concentran en cada tramo; "
                 "son pistas para ubicarse, no un resumen. Verifica en la transcripción con `ask`.")
    return "\n".join(lines)
