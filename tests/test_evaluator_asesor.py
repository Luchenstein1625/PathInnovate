import unittest
from copilot.evaluator_asesor import parse, score

class TestParse(unittest.TestCase):
    def test_lista_con_prefijo_recomendacion(self):
        self.assertEqual(parse("RECOMENDACION: API_RAG, ML_TABULAR, VERIFICADOR. Esta combinacion usa API_RAG"),
                         ("C", {"API_RAG", "ML_TABULAR", "VERIFICADOR"}))
    def test_etiqueta_simple_no_cambia(self):
        self.assertEqual(parse("RECOMENDACION: SLM_PROPIO  \nPorque REGLAS y VERIFICADOR"), ("R", "SLM_PROPIO"))
    def test_componentes_y_parcial(self):
        q = {"gold": "COMPONENTES: SLM_PROPIO + REGLAS + VERIFICADOR + HUMANO"}
        r = score(q, "RECOMENDACION: SLM_PROPIO\nok", [], False)
        self.assertFalse(r["correcta"]); self.assertTrue(r["subdim"]); self.assertEqual(r["parcial"], 0.25)
        self.assertTrue(score(q, "COMPONENTES: SLM_PROPIO, REGLAS, VERIFICADOR, HUMANO", [], False)["correcta"])
if __name__ == "__main__":
    unittest.main()


class TestCifrasDelUsuario(unittest.TestCase):
    def test_cifra_del_usuario_no_es_invencion(self):
        from copilot.verifier import GroundingVerifier as G
        ch = [{"text": "Con menos de 50 preguntas distintas use reglas."}]
        self.assertFalse(G.verify_facts("Son 15 preguntas, use reglas [1]", ch)[0])
        self.assertTrue(G.verify_facts("Son 15 preguntas, use reglas [1]", ch, "Recibo 20 consultas con 15 preguntas")[0])
        self.assertFalse(G.verify_facts("Costara 99 dolares [1]", ch, "Recibo 20 consultas con 15 preguntas")[0])
