import unittest
from copilot.advisor import decide
from copilot.llm import load_env
import os, tempfile


class TestAdvisor(unittest.TestCase):
    def test_faq_pequena_no_necesita_llm(self):
        d = decide("faq", 600, 1.5, preguntas_distintas=15)
        self.assertEqual(d["peldano_tecnico"], "REGLAS")
        self.assertTrue(any(s["alternativa"] == "AGENTE" for s in d["sobreventa_evitada"]))

    def test_consulta_docs_con_pocas_preguntas_es_faq(self):
        d = decide("consulta_docs", 300, 1, preguntas_distintas=12)
        self.assertEqual(d["peldano_tecnico"], "REGLAS")

    def test_herramienta_existente(self):
        self.assertEqual(decide("faq", 500, 1, herramienta_existente=True)["peldano_tecnico"], "NO_IA")

    def test_banca_regulada_agrega_verificador_y_humano(self):
        d = decide("consulta_docs", 20000, 2, regulado=True, privacidad=True)
        self.assertEqual(d["peldano_tecnico"], "SLM_PROPIO")
        self.assertTrue({"VERIFICADOR", "HUMANO"} <= set(d["componentes"]))

    def test_prediccion_pocos_datos_no_ml(self):
        self.assertEqual(decide("prediccion", 2000, 3, etiquetados=80)["peldano_tecnico"], "REGLAS")
        self.assertEqual(decide("prediccion", 2000, 3, etiquetados=5000)["peldano_tecnico"], "ML_TABULAR")

    def test_no_se_paga_no_recomienda_gastar(self):
        d = decide("consulta_docs", 100, 0.5)
        self.assertEqual(d["recomendacion"], "NO_AUTOMATIZAR_AUN")

    def test_agente_solo_si_pasos_variables(self):
        self.assertEqual(decide("accion", 5000, 4)["peldano_tecnico"], "REGLAS")
        self.assertEqual(decide("accion", 5000, 4, pasos_variables=True)["peldano_tecnico"], "AGENTE")

    def test_env_con_comentarios_en_linea(self):
        with tempfile.TemporaryDirectory() as t:
            p = os.path.join(t, ".env")
            open(p, "w", encoding="utf-8").write("ZZ_PROV=huggingface            # openai | huggingface\r\nZZ_M=\"a # b\"\r\n")
            load_env(p)
            self.assertEqual(os.environ["ZZ_PROV"], "huggingface")
            self.assertEqual(os.environ["ZZ_M"], "a # b")


if __name__ == "__main__":
    unittest.main()
