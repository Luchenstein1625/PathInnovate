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
