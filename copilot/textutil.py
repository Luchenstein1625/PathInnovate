"""Utilidades de texto: normalización sin tildes y tokenización para BM25."""

import re
import unicodedata

STOP = set(
    """
    de la el en y a los las del se que por un una con para es al lo como mas pero sus le ya o fue este si
    porque esta son entre cuando muy sin sobre tambien me hasta hay donde quien desde todo nos durante todos
    uno les ni contra otros ese eso ante ellos e esto mi antes algunos que unos yo otro otras otra el tanto
    esa estos mucho quienes nada muchos cual poco ella estar estas algunas algo nosotros ser son esta
    the of and to in is it that for on with as are this be by or an at from not but have has was were
    if then so we you they can will just like yes no ok eh bueno entonces pues vamos
    """.split()
)


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def norm(s: str) -> str:
    """Minúsculas, sin tildes, solo [a-z0-9] separados por un espacio."""
    return re.sub(r"[^a-z0-9]+", " ", strip_accents(s).lower()).strip()


def tokenize(s: str) -> list:
    return [t for t in re.findall(r"[a-z0-9]+", strip_accents(s).lower()) if len(t) > 1 and t not in STOP]


# Muletillas del habla en clases grabadas: se usan solo para resumir temas (outline), no para buscar.
FILLER = set(
    """
    bien va aqui aca alla ahi asi tiene tienen puede pueden sea te tu ver voy van vamos claro ahora cada parte
    hacer hace hacen entonces ya digamos cosa cosas poco dos mismo misma tambien hay esta estan era fue ser tener
    tengo veces siempre solo bueno pues eh mmm algo alguien nadie mas mucho muy cuando donde como cual quien porque
    cierto sabe saben quiero dijo dice decir ejemplo ejemplos tipo forma vez vale perfecto gracias ok nada todo
    todos toda todas aquel aquello esos esas estas ese esa eso este esto puedo pueda tenemos tenga podemos podria
    mira miren miremos digo etcetera directamente primero segundo tercero final luego despues antes ademas aun
    """.split()
)


def _fold(text: str) -> str:
    """Minúsculas y sin tildes, conservando la longitud para poder mapear posiciones al texto original."""
    out = []
    for c in text:
        s = strip_accents(c)
        out.append((s if len(s) == 1 else c).lower())
    return "".join(out)


def snippet(text: str, query: str, width: int = 320) -> str:
    """Recorte del texto centrado en la primera palabra de la consulta que aparezca."""
    plain = _fold(text)
    pos = [plain.find(t) for t in set(tokenize(query)) if plain.find(t) >= 0]
    if not pos or len(text) <= width:
        return text[:width] + ("..." if len(text) > width else "")
    start = max(0, min(pos) - width // 3)
    start = text.rfind(" ", 0, start) + 1 if start else 0
    end = min(len(text), start + width)
    if end < len(text):
        end = text.rfind(" ", start, end) if text.rfind(" ", start, end) > start else end
    return ("..." if start else "") + text[start:end].strip() + ("..." if end < len(text) else "")
