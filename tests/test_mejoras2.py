import unittest
from types import SimpleNamespace as NS
from copilot.verifier import GroundingVerifier as V
from copilot.evaluator import run_benchmark, load_eval

CH = [{"text": "Entrega del informe: domingo 8 de noviembre de 2026, hasta las 23:59 (hora de Chile)."}]


class NoCita:
    openai_model, local_model_id, device_label = "f", "f", "cpu"
    def _r(self, p, s):
        return NS(answer="La entrega del informe vence el 8 de noviembre a las 23:59.", latency_seconds=.1, cost_usd=0, prompt_tokens=10, completion_tokens=5)
    generate_openai = generate_local_hf = lambda self, p, s="": self._r(p, s)


class T(unittest.TestCase):
    def test_adjunta_cita_respaldada(self):
        out = V.attach_citations("La entrega del informe vence el 8 de noviembre a las 23:59.", CH)
        self.assertTrue(out.endswith("[1]")); self.assertTrue(V.verify_citations(out, CH)[0])

    def test_no_inventa_respaldo(self):
        a = "La entrega vence en 77 páginas."
        self.assertEqual(V.attach_citations(a, CH), a)

    def test_no_toca_si_ya_cita_o_abstiene(self):
        self.assertEqual(V.attach_citations("Dato [1].", CH), "Dato [1].")
        self.assertEqual(V.attach_citations("NO_HAY_INFORMACION", CH), "NO_HAY_INFORMACION")

    def test_hibrido_repara_sin_reintentar(self):
        pre, cor = load_eval(); r = run_benchmark(NoCita(), pre[:1], cor, 1, True)
        for c in ("hibrido", "hibrido_local"):
            m = r["configs"][c]["metricas"]
            self.assertEqual((m["reparadas"], m["reintentos"], m["correctas"]), (1.0, 0.0, 1.0))
        self.assertEqual(r["configs"]["rag_local"]["metricas"]["sin_cita"], 1.0)

if __name__ == "__main__":
    unittest.main()
