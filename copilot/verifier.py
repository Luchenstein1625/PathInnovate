import re
import unicodedata
from typing import List, Dict, Any, Tuple

_NUM = re.compile(r"(?<![\w\[])\d+(?:[.,]\d+)?(?![\w\]])")


def _n(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")


class GroundingVerifier:
    """Verificador simbolico: (1) citas [n] existentes, (2) cada cifra/fecha de la respuesta debe
    aparecer en el contexto citado, (3) el grafo de precedencias es aciclico."""

    @staticmethod
    def verify_citations(response_text: str, context_chunks: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        valid = {str(i + 1) for i in range(len(context_chunks))}
        cited = set(re.findall(r"\[(\d+)\]", response_text))
        bad = cited - valid
        return (not bad and len(cited) > 0), [f"Cita inexistente [{c}] detectada." for c in sorted(bad)]

    @staticmethod
    def verify_facts(response_text: str, context_chunks: List[Dict[str, Any]], user_text: str = "") -> Tuple[bool, List[str]]:
        """Toda cifra de la respuesta (sin contar las citas [n]) debe estar en algun fragmento
        o en la pregunta del usuario (user_text): repetir un dato que el usuario dio no es una invencion."""
        ctx = _n(" ".join([c["text"] for c in context_chunks] + [user_text])).replace(",", ".")
        ctx_nums = {x.replace(",", ".") for x in _NUM.findall(ctx)}
        loose = [x.replace(",", ".") for x in _NUM.findall(re.sub(r"\[\d+\]", " ", _n(response_text)))]
        miss = sorted({x for x in loose if x not in ctx_nums})
        return not miss, [f"Cifra sin respaldo en el contexto: {x}" for x in miss]

    @staticmethod
    def attach_citations(answer: str, context_chunks: List[Dict[str, Any]]) -> str:
        """Repara respuestas sin citas: agrega [n] a cada oración que tenga respaldo léxico en un fragmento
        (todas sus cifras presentes y >=2 palabras de contenido en común). No inventa respaldo: lo que no se
        puede respaldar queda sin cita y el verificador lo rechaza. Es una heurística léxica, no semántica."""
        if re.search(r"\[\d+\]", answer) or "NO_HAY_INFORMACION" in answer:
            return answer
        out = []
        for sent in re.split(r"(?<=[.!?])\s+", answer.strip()):
            nums = {x.replace(",", ".") for x in _NUM.findall(_n(sent))}
            toks = {t for t in re.findall(r"\w+", _n(sent)) if len(t) > 3}
            best, best_sc = None, 0
            for i, c in enumerate(context_chunks):
                ct = _n(c["text"]).replace(",", ".")
                if not nums <= set(_NUM.findall(ct)):
                    continue
                sc = len(toks & set(re.findall(r"\w+", ct)))
                if sc > best_sc:
                    best, best_sc = i, sc
            out.append(f"{sent} [{best + 1}]" if best is not None and best_sc >= 2 else sent)
        return " ".join(out)

    @staticmethod
    def validate_precedence_graph(tasks: List[Dict[str, Any]]) -> Tuple[bool, str]:
        adj = {t["id"]: t.get("depends_on", []) for t in tasks}
        state = {}

        def cyc(v):
            state[v] = 1
            for w in adj.get(v, []):
                if state.get(w) == 1 or (state.get(w, 0) == 0 and cyc(w)):
                    return True
            state[v] = 2
            return False

        for n in adj:
            if state.get(n, 0) == 0 and cyc(n):
                return False, f"Ciclo de dependencia circular detectado involucrando la tarea '{n}'."
        return True, "Grafo de dependencias válido y acíclico."
