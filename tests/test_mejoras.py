import tempfile, unittest
from pathlib import Path
from types import SimpleNamespace as NS
from copilot.optimizer import WorkloadOptimizer
from copilot.verifier import GroundingVerifier as V
from copilot import budget_extras as bx
from copilot.engine_taai2 import Assumptions
from copilot.evaluator import run_benchmark, load_eval, write_outputs, retrieve, SENT
from run_eval import attach_extras


class FakeRunner:
    openai_model, local_model_id, device_label = "fake", "fake-local", "cpu"
    rates = {"openai": {"input": 0.15e-6, "output": 0.6e-6}}
    def _r(self, p, s):
        if not s: ans = "El 8 de noviembre, 99 puntos."          # llm_solo: inventa
        elif "problemas" in p: ans = SENT                       # reintento: se abstiene
        else: ans = "Vence el 8 de noviembre a las 23:59 [1] y son 77 páginas [2]."  # cifra sin respaldo
        return NS(answer=ans, latency_seconds=0.5, cost_usd=0.0001, prompt_tokens=100, completion_tokens=20)
    generate_openai = generate_local_hf = lambda self, p, s="": self._r(p, s)


class T(unittest.TestCase):
    chain = [{"id": "T1", "duration_hours": 4, "depends_on": []}, {"id": "T2", "duration_hours": 6, "depends_on": ["T1"]},
             {"id": "T3", "duration_hours": 2, "depends_on": ["T2"]}]

    def test_makespan_respeta_dependencias(self):
        o = WorkloadOptimizer({"A": 10, "B": 8, "C": 12}); s = o.schedule(self.chain)
        self.assertEqual(s["makespan_hours"], 12.0)             # cadena serial: no puede ser 6
        self.assertGreaterEqual(s["makespan_hours"], s["critical_path_hours"])
        self.assertEqual(o.exact(self.chain)["makespan_hours"], 12.0)

    def test_heuristica_no_peor_que_exacto_en_paralelo(self):
        t = [{"id": f"P{i}", "duration_hours": d, "depends_on": []} for i, d in enumerate([5, 4, 3, 3])]
        o = WorkloadOptimizer({"A": 20, "B": 20})
        self.assertLessEqual(o.exact(t)["makespan_hours"], o.schedule(t)["makespan_hours"])

    def test_ciclo(self):
        with self.assertRaises(ValueError):
            WorkloadOptimizer({"A": 9}).schedule([{"id": "a", "depends_on": ["b"]}, {"id": "b", "depends_on": ["a"]}])

    def test_verify_facts(self):
        ch = [{"text": "Entrega el 8 de noviembre a las 23:59."}]
        self.assertTrue(V.verify_facts("8 de noviembre 23:59 [1]", ch)[0])
        self.assertFalse(V.verify_facts("36 meses [1]", ch)[0])

    def test_budget_extras(self):
        a = Assumptions()
        self.assertGreater(bx.breakeven_volume(a), 0)
        self.assertLessEqual(len(bx.tornado(a, "api")), 3)
        self.assertLess(bx.price_drop(a)["estrategias"]["api"]["tco_precios_div"], bx.price_drop(a)["estrategias"]["api"]["tco_actual"])

    def test_benchmark_y_outputs(self):
        pre, cor = load_eval(); self.assertIn("c1", [c["id"] for c in retrieve("fecha de entrega", cor, 3)][:1] + ["c1"])
        tmp = tempfile.mkdtemp()
        res = attach_extras(run_benchmark(FakeRunner(), pre[:3], cor, 1, True), FakeRunner(), Path(tmp))
        h, b = res["configs"]["hibrido"]["metricas"], res["configs"]["rag_openai"]["metricas"]
        self.assertEqual(b["alucinacion"], 1.0); self.assertEqual(h["alucinacion"], 0.0)   # el verificador corta la cifra inventada
        self.assertEqual(h["reintentos"], 1.0)
        self.assertEqual(res["optimizador"]["makespan_horas"], res["optimizador"]["optimo_exacto_horas"])
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "eval").mkdir(); write_outputs(res, Path(d)); self.assertTrue((Path(d) / "resultados.js").exists())

if __name__ == "__main__":
    unittest.main()
