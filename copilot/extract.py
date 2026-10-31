"""Extractores de texto por formato. Cada uno devuelve (unidades, info), con unidades = [(ubicación, texto)]."""

import json
import re
from pathlib import Path

VTT_CUE = re.compile(r"^\s*((?:\d+:)?\d{1,2}:\d{2}[.,]\d{1,3})\s*-->")
TIME = re.compile(r"(?<!\d)(\d{1,2}:\d{2}(?::\d{2})?)(?:[.,]\d{1,3})?(?!\d)")
SEG_WORDS = 60  # largo máximo de un segmento al ubicar texto sin tiempos
CHAT_NOISE = re.compile(r"^(reacted to|se ha reaccionado|replying to|respondiendo a|has reacted)", re.I)
CHAT_NAME = re.compile(r"^[^\t:]{1,60}:\s*")


def read_text(path):
    data = Path(path).read_bytes()
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            pass
    return data.decode("latin-1", errors="replace")


def _hms(seconds):
    seconds = int(seconds)
    return f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


def extract_cues(text):
    """VTT / SRT: una unidad por bloque de subtítulo, ubicada por el tiempo de inicio."""
    units, cur, loc = [], [], ""
    for line in text.splitlines():
        m = VTT_CUE.match(line)
        if m:
            if cur:
                units.append((loc, " ".join(cur)))
                cur = []
            loc = re.split(r"[.,]", m.group(1))[0]
            if loc.count(":") == 1:  # mm:ss -> hh:mm:ss
                loc = "00:" + loc
            continue
        s = line.strip()
        if not s or s.upper().startswith("WEBVTT") or s.isdigit() or s.startswith("NOTE"):
            continue
        cur.append(re.sub(r"<[^>]+>", "", s))
    if cur:
        units.append((loc, " ".join(cur)))
    return units, {}


def extract_tsv(text):
    """TSV de Whisper: columnas start, end (milisegundos) y text."""
    units = []
    for line in text.splitlines()[1:]:
        parts = line.split("\t", 2)
        if len(parts) == 3 and parts[0].strip().isdigit() and parts[2].strip():
            units.append((_hms(int(parts[0]) / 1000), parts[2].strip()))
    return units, {}


def _positional(lines):
    """Texto sin tiempos: ubica cada segmento por su posición relativa (≈ % de la clase)."""
    total = sum(len(l) + 1 for l in lines) or 1
    units, pos = [], 0
    for line in lines:
        words = line.split()
        for i in range(0, len(words), SEG_WORDS):
            seg = " ".join(words[i : i + SEG_WORDS])
            units.append((f"≈{int(100 * pos / total)}%", seg))
            pos += len(seg) + 1
    return units


def extract_plain(text, chat=False):
    """TXT de transcripción o de chat.

    Con hora al inicio de la línea (chats de Zoom) usa esa hora; sin horas (transcripciones .txt, a veces
    de un solo párrafo gigante) ubica por posición relativa en lugar de dar un inútil "l.1".
    """
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    timed = sum(1 for l in lines if (m := TIME.search(l)) and m.start() <= 12)
    if not lines:
        return [], {}
    if timed / len(lines) < 0.3:
        return _positional(lines), {"sin_tiempo": True}
    units, loc = [], ""
    for line in lines:
        s = line
        m = TIME.search(s)
        if m and m.start() <= 12:
            loc = m.group(1)
            s = (s[: m.start()] + " " + s[m.end():]).strip(" []-:\t")
        if chat:
            s = CHAT_NAME.sub("", s, count=1).strip()
            if CHAT_NOISE.match(s):
                continue
        if s:
            units.append((loc or "inicio", s))
    return units, {}


def extract_md(text):
    units, loc = [], ""
    for line in text.splitlines():
        h = re.match(r"^#{1,6}\s+(.*)", line)
        if h:
            loc = h.group(1).strip()[:60]
            continue
        if line.strip():
            units.append((loc or "inicio", line.strip()))
    return units, {}


def extract_pdf(path):
    from pypdf import PdfReader

    r = PdfReader(str(path))
    if r.is_encrypted:
        try:
            r.decrypt("")
        except Exception:
            return [], {"error": "PDF cifrado"}
    units, empty = [], 0
    for i, page in enumerate(r.pages, 1):
        try:
            t = page.extract_text() or ""
        except Exception:
            t = ""
        if t.strip():
            units.append((f"p.{i}", t))
        else:
            empty += 1
    return units, {"paginas": len(r.pages), "sin_texto": empty}


def extract_pptx(path):
    from pptx import Presentation

    units = []
    for i, slide in enumerate(Presentation(str(path)).slides, 1):
        parts = []
        for sh in slide.shapes:
            if getattr(sh, "has_text_frame", False) and sh.has_text_frame:
                parts.append(sh.text_frame.text)
            if getattr(sh, "has_table", False) and sh.has_table:
                for row in sh.table.rows:
                    parts.append(" | ".join(c.text for c in row.cells))
        if slide.has_notes_slide and slide.notes_slide.notes_text_frame is not None:
            parts.append(slide.notes_slide.notes_text_frame.text)
        text = "\n".join(p for p in parts if p and p.strip())
        if text.strip():
            units.append((f"diap.{i}", text))
    return units, {}


def extract_docx(path):
    import docx

    d = docx.Document(str(path))
    units = [(f"párr.{i}", p.text) for i, p in enumerate(d.paragraphs, 1) if p.text.strip()]
    for ti, table in enumerate(d.tables, 1):
        for row in table.rows:
            units.append((f"tabla {ti}", " | ".join(c.text.strip() for c in row.cells)))
    return units, {}


def extract_ipynb(path):
    nb = json.loads(read_text(path))
    units = []
    for i, cell in enumerate(nb.get("cells", []), 1):
        src = cell.get("source", "")
        src = "".join(src) if isinstance(src, list) else src
        if src.strip():
            units.append((f"celda {i}", src[:2000]))
    return units, {}


def extract(path, kind=""):
    ext = Path(path).suffix.lower()
    if ext == ".pdf":
        return extract_pdf(path)
    if ext == ".pptx":
        return extract_pptx(path)
    if ext == ".docx":
        return extract_docx(path)
    if ext == ".ipynb":
        return extract_ipynb(path)
    text = read_text(path)
    if ext in (".vtt", ".srt"):
        return extract_cues(text)
    if ext == ".tsv":
        return extract_tsv(text)
    if ext == ".md":
        return extract_md(text)
    return extract_plain(text, chat=(kind == "chat"))
