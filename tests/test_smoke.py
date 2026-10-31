"""Pruebas sobre un árbol sintético que imita el formato real del magíster (vtt, srt, tsv, txt sin tiempos, chats)."""

import csv
import tempfile
import unittest
from pathlib import Path

from copilot import outline as outlinemod, planner, scan as scanmod, trace as tracemod
from copilot.cli import resolve_root
from copilot.extract import extract_plain, extract_tsv
from copilot.index import Index, build, chunk_units
from copilot.textutil import snippet

S4_LINES = [
    "Hoy vemos planificación clásica con STRIPS y PDDL, precondiciones y efectos.",
    "Un planificador HTN permite replanificación cuando falla una acción.",
]
FILLER = [f"Texto de relleno número {i} sobre otros temas distintos del curso." for i in range(10, 50)]
ADMIN = [f"Aviso {i}: la fecha de entrega y la sala del semestre cambian según el grupo {i * 7}." for i in range(40)]
CLOSING = [f"Cierre {i}: recordatorio breve de la próxima clase con ejemplo {i * 3} y lecturas." for i in range(8)]


def vtt(lines, repeat=1):
    out, t = ["WEBVTT", ""], 5
    for _ in range(repeat):
        for line in lines:
            out += [f"00:{t // 60:02d}:{t % 60:02d}.000 --> 00:{(t + 4) // 60:02d}:{(t + 4) % 60:02d}.000", line, ""]
            t += 5
    return "\n".join(out)


def make_tree(root: Path):
    def w(rel, text=""):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    w("README.md", "# readme")
    w("01_Introduccion_IA.md", "# Intro\nLa IA estudia agentes inteligentes y representación del conocimiento. " * 5)
    w("15_Topicos_Avanzados_IA_II.md", "# TAAI2\nResumen: RAG, LoRA y destilación son técnicas de adaptación de un LLM. " * 5)
    w("02 REPRESENTACIÓN DE CONOCIMIENTOS Sec.1 FIC/Clase 1.srt",
      "1\n00:00:01,000 --> 00:00:04,000\nUna ontología y un grafo de conocimiento restringen las reglas del sistema experto.\n\n"
      "2\n00:00:05,000 --> 00:00:09,000\nLa lógica de primer orden permite inferencia y razonamiento simbólico en el verificador.\n")
    d16 = "16 TÓPICOS AVANZADOS EN INTELIGENCIA ARTIFICIAL 2"
    w(f"{d16}/GMT20260921-194836_Recording.cc.vtt",
      vtt(["Para adaptar un LLM usamos RAG, LoRA y destilación de modelos en el curso."] + FILLER))
    w(f"{d16}/GMT20260928-195740_Recording.cc.vtt", vtt(ADMIN))
    s4 = vtt(S4_LINES + CLOSING[:6], repeat=5)
    w(f"{d16}/GMT20261019-200100_Recording.cc.vtt", s4)
    # la misma clase en .txt (sin tiempos) y en .tsv, más una copia con otro nombre en una subcarpeta
    w(f"{d16}/GMT20261019-200100_Recording.txt", "\n".join(S4_LINES + CLOSING[:6]) * 5)
    w(f"{d16}/GMT20261019-200100_Recording.tsv",
      "start\tend\ttext\n" + "\n".join(f"{i * 5000}\t{i * 5000 + 4000}\t{l}" for i, l in enumerate((S4_LINES + CLOSING[:6]) * 5)))
    w(f"{d16}/copias/clase_s4_copia.txt", "\n".join(S4_LINES + CLOSING[:6]) * 5)
    w("03 TÉCNICAS DE BÚSQUEDA Y HEURÍSTICAS/Clase1.txt",
      "00:00:03 El algoritmo genético y el recocido simulado son metaheurísticas para optimización con función objetivo.\n" * 6)
    # un solo párrafo gigante sin tiempos, como las transcripciones .txt de Zoom
    w("04 APRENDIZAJE AUTOMÁTICO Sec.1 FIC/Clase 1/Clase 1 - Zoom.txt",
      " ".join(f"palabra{i}" for i in range(150)) + " aquí explicamos el aprendizaje por refuerzo y Q-learning con recompensas "
      + " ".join(f"otra{i}" for i in range(150)))
    w("04 APRENDIZAJE AUTOMÁTICO Sec.1 FIC/Clase 1/Clase 1 - Chat.txt",
      "00:10:01\tJuan Perez:\tHola profe, ¿me pasa el link del notebook de clustering?\n"
      "00:10:20\tAna Gómez:\tReacted to \"Hola profe\" with 👍\n"
      "00:11:05\tAna Gómez:\tGracias, ya descargué el notebook y estoy probando el ejemplo\n"
      "00:12:40\toperador zoom:\tReplying to \"Gracias\"\n")
    w("Otros/A - Introducción a Python/Ejemplos/01_print.py", "print('hola')")
    w("Otros/13 CAPSTONE/Presentacion.txt", "Capacity planning del banco, información confidencial " * 10)
    w("Otros/00 Intro/0 - Libros - Papers - Textos Generales/libro.txt", "Un libro de texto general sobre inteligencia artificial moderna. " * 30)
    w("Otros/web/index.html", "<html></html>")

    import docx
    d = docx.Document()
    d.add_paragraph("Taller de diseño: la innovación se valida con prototipos y un modelo de negocio.")
    (root / "11 TALLER DE DISEÑO E INNOVACIÓN").mkdir(parents=True, exist_ok=True)
    d.save(str(root / "11 TALLER DE DISEÑO E INNOVACIÓN/notas.docx"))
    from pptx import Presentation
    prs = Presentation()
    s = prs.slides.add_slide(prs.slide_layouts[1])
    s.shapes.title.text = "Arquitectura de agentes"
    s.placeholders[1].text = "Un orquestador coordina agentes con herramientas, memoria y humano en el circuito."
    (root / "05 Agentes Inteligentes/Clase 1").mkdir(parents=True, exist_ok=True)
    prs.save(str(root / "05 Agentes Inteligentes/Clase 1/arq.pptx"))


class Smoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.base = Path(cls.tmp.name)
        cls.root = cls.base / "MAGISTER"
        cls.data = cls.base / "data"
        make_tree(cls.root)
        cls.rows = scanmod.scan(cls.root)
        scanmod.write_inventory(cls.rows, cls.data / "inventory.csv")
        cls.stats = build(cls.rows, cls.root, cls.data)
        cls.idx = Index(cls.data)
        cls.topics = tracemod.load_topics(Path("does-not-exist.csv"))  # cae a los valores por defecto

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def by_rel(self, fragment):
        return [r for r in self.rows if fragment in r["rel"]]

    # ---- inventario
    def test_course_mapping_and_root_md(self):
        r = self.by_rel("15_Topicos_Avanzados_IA_II.md")[0]
        self.assertEqual((r["course"], r["kind"]), ("16", "resumen"))
        self.assertEqual(self.by_rel("README.md")[0]["status"], "meta")
        self.assertEqual(self.by_rel("Clase 1.srt")[0]["course"], "02")

    def test_exclusions_and_include_flags(self):
        excluded = {r["rel"] for r in self.rows if r["kind"] == "dir"}
        self.assertTrue(any("Python" in e for e in excluded))
        self.assertTrue(any("CAPSTONE" in e for e in excluded))
        self.assertTrue(any(e.endswith("web/") for e in excluded))
        self.assertFalse(self.by_rel("Presentacion.txt"))
        rows = scanmod.scan(self.root, include_otros=True, include_capstone=True)
        self.assertTrue([r for r in rows if "Presentacion.txt" in r["rel"]])

    def test_session_and_date_from_filename(self):
        r = self.by_rel("GMT20261019-200100_Recording.cc.vtt")[0]
        self.assertEqual((r["fecha"], r["session"]), ("2026-10-19", "S4"))
        self.assertEqual(self.by_rel("Clase1.txt")[0]["session"], "")

    def test_same_class_in_several_formats_is_deduplicated(self):
        base = "GMT20261019-200100_Recording"
        status = {r["rel"].split("/")[-1]: r["status"] for r in self.rows if base in r["rel"] or "copia" in r["rel"]}
        self.assertEqual(status[base + ".cc.vtt"], "indexar")
        self.assertEqual(status[base + ".txt"], "duplicado")
        self.assertEqual(status[base + ".tsv"], "duplicado")
        copia = self.by_rel("clase_s4_copia.txt")[0]  # otra carpeta y otro nombre: se detecta por contenido
        self.assertEqual(copia["status"], "duplicado")
        self.assertIn("mismo contenido", copia["note"])

    def test_distinct_classes_are_not_merged(self):
        d16 = [r for r in self.rows if r["course"] == "16" and r["kind"] == "transcript" and r["status"] == "indexar"]
        self.assertEqual(len(d16), 3)

    # ---- extractores
    def test_tsv_uses_milliseconds(self):
        units, _ = extract_tsv("start\tend\ttext\n0\t4000\thola\n65000\t70000\tsegunda línea")
        self.assertEqual(units, [("00:00:00", "hola"), ("00:01:05", "segunda línea")])

    def test_text_without_times_is_located_by_position(self):
        hits = self.idx.search("aprendizaje por refuerzo Q-learning recompensas", k=1, course="04")
        self.assertTrue(hits)
        self.assertTrue(hits[0]["loc"].startswith("≈"), hits[0]["loc"])
        units, info = extract_plain("una línea sin horas " * 100)
        self.assertTrue(info.get("sin_tiempo"))
        self.assertGreater(len(units), 1)  # un párrafo gigante se parte en segmentos

    def test_chat_drops_speaker_names_and_reactions(self):
        text = " ".join(c["text"] for c in self.idx.chunks if c["kind"] == "chat")
        self.assertIn("link del notebook", text)
        for noise in ("Juan Perez", "Ana Gómez", "Reacted to", "operador zoom", "Replying to"):
            self.assertNotIn(noise, text)

    # ---- índice y búsqueda
    def test_ingest_counts_and_no_errors(self):
        self.assertGreater(self.stats["chunks"], 5)
        self.assertEqual(self.stats["errores"], [])

    def test_search_cites_timestamp_and_session(self):
        hits = self.idx.search("planificación STRIPS PDDL", k=3, course="16")
        self.assertTrue(hits)
        self.assertEqual((hits[0]["course"], hits[0]["session"]), ("16", "S4"))
        self.assertRegex(hits[0]["loc"], r"^\d\d:\d\d:\d\d")
        only_s1 = self.idx.search("planificación STRIPS PDDL", k=3, session="S1")
        self.assertTrue(all(h["session"] == "S1" for h in only_s1))

    def test_per_file_limit(self):
        many = self.idx.search("aviso fecha entrega sala semestre", k=10, course="16")
        capped = self.idx.search("aviso fecha entrega sala semestre", k=10, course="16", per_file=1)
        files = [h["file"] for h in capped]
        self.assertEqual(len(files), len(set(files)))
        self.assertGreaterEqual(len(many), len(capped))

    def test_snippet_is_centered_on_the_query(self):
        text = "uno dos tres " * 40 + "aquí hablamos de destilación de modelos en detalle " + "cuatro cinco " * 40
        self.assertIn("destilación", snippet(text, "destilacion modelos", width=200))

    # ---- trazabilidad
    def test_trace_states(self):
        res = {r["id"]: r["estado_material"] for r in tracemod.trace(self.idx, self.topics)}
        self.assertEqual(res["S1.2"], "dictado en S1")
        self.assertEqual(res["S4.1"], "dictado en S4")
        self.assertEqual(res["S2.1"], "solo cursos de apoyo")  # S2 grabada sin ese contenido; sí está en el curso 05
        self.assertEqual(res["S2.4"], "SIN MATERIAL")
        self.assertEqual(res["S6.5"], "SESIÓN SIN GRABACIÓN")  # S6 aún no tiene grabación

    def test_one_loose_word_is_not_strong_evidence(self):
        # "token" solo, una vez, no basta para decir que el tópico se dictó
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "MAGISTER"
            f = root / "16 TÓPICOS AVANZADOS EN INTELIGENCIA ARTIFICIAL 2" / "GMT20260921-194836_Recording.cc.vtt"
            f.parent.mkdir(parents=True)
            f.write_text(vtt(["Hoy hablamos de tokens y de otras cosas sin relación con costos ni contexto."] + FILLER),
                         encoding="utf-8")
            rows = scanmod.scan(root)
            build(rows, root, Path(d) / "data")
            res = {r["id"]: r["estado_material"] for r in tracemod.trace(Index(Path(d) / "data"), self.topics)}
            self.assertEqual(res["S1.3"], "mención débil en S1")

    def test_check_flags_missing_and_mentions(self):
        draft = self.base / "borrador.md"
        draft.write_text(
            "# 5. Planificación\nUsamos STRIPS y PDDL con precondiciones y efectos. STRIPS define acciones.\n"
            "# 2. Modelos fundacionales\nSolo mencionamos HTN aquí.\n# 8. Presupuesto\nTCO.\n", encoding="utf-8")
        res = tracemod.check(draft, self.topics)
        states = {r["id"]: r["estado"] for r in res["topicos"]}
        self.assertEqual(states["S4.1"], "desarrollado (revisar a mano)")
        self.assertEqual(states["S4.2"], "MENCIONADO FUERA DE SU SECCIÓN")
        self.assertEqual(states["S6.5"], "AUSENTE")
        self.assertIn("12 (recomendacion)", res["secciones_faltantes"])

    # ---- temario
    def test_outline_lists_sessions_and_terms(self):
        text = outlinemod.outline(self.idx, ["16"], window_min=15, top=6)
        self.assertIn("S4 · 2026-10-19", text)
        self.assertIn("recordatorio breve", text)
        self.assertIn("No hay transcripciones", outlinemod.outline(self.idx, ["99"]))

    # ---- raíz del proyecto
    def test_resolve_root(self):
        self.assertEqual(resolve_root("/algun/lugar"), Path("/algun/lugar"))
        self.assertEqual(resolve_root(None, "/desde/env"), Path("/desde/env"))
        self.assertEqual(resolve_root(None, None, cwd=self.base), self.base / "MAGISTER")
        with tempfile.TemporaryDirectory() as empty:
            from copilot import cli
            saved = cli.PROJECT_DIR
            cli.PROJECT_DIR = Path(empty)
            try:
                with self.assertRaises(SystemExit):
                    resolve_root(None, None, cwd=empty)
            finally:
                cli.PROJECT_DIR = saved

    # ---- utilidades y plan
    def test_chunking_overlap(self):
        units = [("p.1", " ".join(f"w{i}" for i in range(100)))]
        chunks = chunk_units(units, 40, 10)
        self.assertEqual(len(chunks), 3)
        self.assertTrue(chunks[1][1].startswith("w30"))

    def test_plan_fits_and_respects_dependencies(self):
        with tempfile.TemporaryDirectory() as d:
            planner.write_defaults(d)
            rows, load, cap, spent = planner.plan(d)
            self.assertEqual(len(rows), len(planner.D.SECTIONS))
            end = {r["id"]: r["fin_dia"] for r in rows}
            start = {r["id"]: r["inicio_dia"] for r in rows}
            self.assertNotIn("NO CABE", end.values())
            for sid, _, _, deps, _, _ in planner.D.SECTIONS:
                for dep in [x for x in deps.split(";") if x]:
                    self.assertGreater(start[sid], end[dep])
            with open(Path(d) / "team.csv", newline="", encoding="utf-8-sig") as f:
                self.assertEqual(len(list(csv.DictReader(f))), 4)


if __name__ == "__main__":
    unittest.main()
