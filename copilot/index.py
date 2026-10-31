"""Paso 3-4: trocea el material, construye un índice BM25 propio (sin dependencias) y lo consulta."""

import json
import math
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from . import defaults as D
from .extract import extract
from .textutil import tokenize

K1, B = 1.5, 0.75
# (palabras por trozo, solape). Las grabaciones llevan trozos más largos que las diapositivas.
CHUNK_PARAMS = {"transcript": (220, 40), "chat": (120, 0), "slides": (150, 20), "notebook": (150, 20)}
DEFAULT_CHUNK = (200, 30)


def chunk_units(units, max_words, overlap):
    words, locs = [], []
    for loc, text in units:
        for w in text.split():
            words.append(w)
            locs.append(loc)
    out, n, i = [], len(words), 0
    step = max(1, max_words - overlap)
    while i < n:
        j = min(n, i + max_words)
        a, b = locs[i], locs[j - 1]
        out.append((a if a == b else f"{a}–{b}", " ".join(words[i:j])))
        if j == n:
            break
        i += step
    return out


def build(rows, root, data_dir):
    root, data_dir = Path(root), Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    chunks, postings, doclen = [], defaultdict(list), []
    stats = {"archivos": 0, "errores": [], "sin_texto": [], "pdf_parcial": []}
    for row in rows:
        if row["status"] != "indexar":
            continue
        try:
            units, info = extract(root / row["rel"], row["kind"])
        except Exception as e:  # un archivo roto no debe detener todo el índice
            stats["errores"].append((row["rel"], f"{type(e).__name__}: {e}"))
            continue
        if not units:
            stats["sin_texto"].append(row["rel"])
            continue
        if info.get("sin_texto"):
            stats["pdf_parcial"].append((row["rel"], info["sin_texto"], info["paginas"]))
        stats["archivos"] += 1
        mw, ov = CHUNK_PARAMS.get(row["kind"], DEFAULT_CHUNK)
        for loc, text in chunk_units(units, mw, ov):
            toks = tokenize(text)
            if len(toks) < 5:
                continue
            doc = len(chunks)
            chunks.append({"course": row["course"], "course_name": row["course_name"], "kind": row["kind"],
                           "file": row["rel"], "loc": loc, "session": row.get("session", ""),
                           "fecha": row.get("fecha", ""), "text": text})
            doclen.append(len(toks))
            for term, c in Counter(toks).items():
                postings[term].append([doc, c])
    with open(data_dir / "chunks.jsonl", "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    N = len(chunks)
    avgdl = (sum(doclen) / N) if N else 1.0
    with open(data_dir / "index.json", "w", encoding="utf-8") as f:
        json.dump({"N": N, "avgdl": avgdl, "doclen": doclen, "postings": postings}, f, ensure_ascii=False)
    with open(data_dir / "meta.json", "w", encoding="utf-8") as f:
        json.dump({"root": str(root), "built": datetime.now().isoformat(timespec="seconds"), "chunks": N}, f)
    stats["chunks"] = N
    return stats


def _as_set(value):
    if not value:
        return None
    return {value} if isinstance(value, str) else set(value)


class Index:
    def __init__(self, data_dir):
        data_dir = Path(data_dir)
        if not (data_dir / "index.json").exists():
            raise SystemExit("No hay índice. Ejecuta primero: python -m copilot ingest")
        with open(data_dir / "chunks.jsonl", encoding="utf-8") as f:
            self.chunks = [json.loads(line) for line in f]
        with open(data_dir / "index.json", encoding="utf-8") as f:
            idx = json.load(f)
        self.N, self.avgdl = idx["N"], idx["avgdl"]
        self.doclen, self.postings = idx["doclen"], idx["postings"]

    def sessions(self):
        """Sesiones TAAI2 que tienen texto indexado."""
        return sorted({c["session"] for c in self.chunks if c["course"] == D.TAAI2 and c.get("session")})

    def search(self, query, k=8, course=None, kind=None, session=None, per_file=0):
        courses, sessions = _as_set(course), _as_set(session)
        scores = defaultdict(float)
        for t in set(tokenize(query)):
            plist = self.postings.get(t)
            if not plist:
                continue
            n = len(plist)
            idf = math.log(1 + (self.N - n + 0.5) / (n + 0.5))
            for d, tf in plist:
                c = self.chunks[d]
                if (courses and c["course"] not in courses) or (kind and c["kind"] != kind):
                    continue
                if sessions and c.get("session", "") not in sessions:
                    continue
                scores[d] += idf * tf * (K1 + 1) / (tf + K1 * (1 - B + B * self.doclen[d] / self.avgdl))
        ranked = sorted(((s * D.KIND_WEIGHT.get(self.chunks[d]["kind"], 1.0), d) for d, s in scores.items()),
                        reverse=True)
        out, per = [], Counter()
        for s, d in ranked:
            f = self.chunks[d]["file"]
            if per_file and per[f] >= per_file:
                continue
            per[f] += 1
            out.append(dict(self.chunks[d], score=round(s, 3)))
            if len(out) >= k:
                break
        return out


def cite(h):
    tag = h["course"] + (f"·{h['session']}" if h.get("session") else "")
    return f"[{tag}] {h['file']} @ {h['loc']}"


def build_prompt(question, hits):
    src = "\n\n".join(f"[{i}] ({h['course_name']} · {h['file']} · {h['loc']})\n{h['text']}"
                      for i, h in enumerate(hits, 1))
    return (
        "Responde en español usando SOLO las fuentes numeradas. Cita cada afirmación con [n]. "
        "Si las fuentes no bastan para responder, dilo explícitamente y no inventes.\n\n"
        f"Pregunta: {question}\n\nFuentes:\n{src}\n"
    )
