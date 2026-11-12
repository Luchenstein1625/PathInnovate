import tempfile, unittest
from pathlib import Path
from copilot.engine_taai2 import (BudgetCalculator, SymbolicVerifier, chain_reliability, strips_plan,
                                  optimize_assignment, risk_register, generate_traceability_matrix)

class TestTAAI2(unittest.TestCase):
    def test_reliability(self):
        r = chain_reliability([0.9, 0.9, 0.9], {1: 0.8})
        self.assertAlmostEqual(r["precision_flujo"], 0.729, 3)
        self.assertGreater(r["precision_flujo_con_humano"], r["precision_flujo"])

    def test_budget_three_strategies_and_npv(self):
        c = BudgetCalculator()
        for s in ("api", "slm_self_hosted", "hybrid"):
            e = c.evaluate(s)
            self.assertGreater(e["evaluacion_36_meses"]["tco_total_usd"], e["evaluacion_12_meses"]["tco_total_usd"])
        self.assertEqual(len(c.sensitivity("api")), 3)

    def test_xlsx(self):
        with tempfile.TemporaryDirectory() as d:
            p = BudgetCalculator().export_xlsx(str(Path(d) / "b.xlsx"))
            from openpyxl import load_workbook
            self.assertEqual(load_workbook(p).sheetnames, ["Supuestos", "TCO", "Sensibilidad"])

    def test_verifier_and_plan(self):
        self.assertIn("RULE_HITL", SymbolicVerifier().verify({"presupuesto_usd": 1, "accion_irreversible": True}))
        plan = strips_plan()
        self.assertEqual(plan[-1], "ejecutar"); self.assertIn("verificar", plan)

    def test_optimizer_not_worse_than_greedy(self):
        r = optimize_assignment([5, 3, 8, 2, 7, 4, 6, 1], 3)
        self.assertLessEqual(r["makespan_sa"], r["makespan_greedy"])

    def test_risks_and_trace(self):
        self.assertEqual(risk_register()[0]["score"], max(x["score"] for x in risk_register()))
        self.assertIn("ANEXO A", generate_traceability_matrix("config/topics.csv"))

if __name__ == "__main__":
    unittest.main()


class TestInnovate(unittest.TestCase):
    def test_rules_choose_techniques(self):
        from copilot.innovate import select_components, innovate, to_markdown
        ids = {c["id"] for c in select_components("predecir el riesgo de fraude con datos historicos")}
        self.assertIn("tabular", ids); self.assertIn("autonomia", ids); self.assertIn("texto", ids)
        ids = {c["id"] for c in select_components("asignar turnos y responder consultas de clientes")}
        self.assertTrue({"asignar", "texto"} <= ids)

    def test_evidence_and_markdown(self):
        from copilot.innovate import innovate, to_markdown
        class Fake:
            def search(self, q, k=2, per_file=1):
                return [{"course": "16", "session": "S1", "file": "a.vtt", "loc": "00:01:00"}]
        r = innovate("asistente de atencion de reclamos", Fake())
        self.assertEqual(r["verificacion"]["componentes_sin_evidencia_en_clases"], [])
        self.assertIn("Propuesta de innovacion", to_markdown(r))
        self.assertIn("SIN EVIDENCIA", to_markdown(innovate("asistente de reclamos", None)))


class TestLLM(unittest.TestCase):
    def test_openai_compatible_call_mocked(self):
        import io, json, os
        from unittest import mock
        from copilot import llm
        env = {"LLM_PROVIDER": "huggingface", "LLM_MODEL": "m", "HF_TOKEN": "t"}
        resp = io.BytesIO(json.dumps({"choices": [{"message": {"content": "hola"}}]}).encode())
        with mock.patch.dict(os.environ, env), mock.patch("copilot.llm.load_env"), \
             mock.patch("urllib.request.urlopen", return_value=resp) as u:
            self.assertEqual(llm.complete("x"), "hola")
            self.assertIn("router.huggingface.co", u.call_args[0][0].full_url)

    def test_missing_config_exits(self):
        import os
        from unittest import mock
        from copilot import llm
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch("copilot.llm.load_env"):
            with self.assertRaises(SystemExit):
                llm.complete("x")


class TestPortfolio(unittest.TestCase):
    def test_exacto_supera_o_iguala_voraz(self):
        from copilot.engine_taai2 import select_portfolio, PORTAFOLIO_EJEMPLO
        r = select_portfolio(PORTAFOLIO_EJEMPLO, 12000)
        self.assertGreaterEqual(r["exacto"]["beneficio_neto_mensual_usd"], r["voraz"]["beneficio_neto_mensual_usd"])
        self.assertLessEqual(r["exacto"]["setup_usd"], 12000)
        self.assertEqual(r["combinaciones_evaluadas"], 2 ** len(PORTAFOLIO_EJEMPLO))

    def test_presupuesto_cero(self):
        from copilot.engine_taai2 import select_portfolio
        self.assertEqual(select_portfolio([{"nombre": "a", "setup": 10, "mensual": 0, "ahorro": 5}], 0)["exacto"]["elegidas"], [])
