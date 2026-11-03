import json, unittest
from copilot.evaluator_asesor import ROOT, RANK, COMP, NOINFO

class TestPreguntasExternas(unittest.TestCase):
    def test_formato(self):
        qs = json.loads((ROOT / "eval_asesor" / "preguntas_externas.json").read_text(encoding="utf-8"))
        self.assertEqual(len({q["id"] for q in qs}), len(qs))
        for q in qs:
            g = q["gold"]
            if g.startswith("COMPONENTES:"):
                toks = [t.strip() for t in g.split(":", 1)[1].split("+")]
                self.assertTrue(toks and all(t in COMP for t in toks), g)
            else:
                self.assertTrue(g in RANK or g == NOINFO, g)
            self.assertGreater(len(q["q"]), 20)
if __name__ == "__main__":
    unittest.main()
