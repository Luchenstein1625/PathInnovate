import unittest
from copilot.engine_taai2 import select_portfolio

class TestFeedback(unittest.TestCase):
    def test_dependencies_and_hours_change_selection(self):
        items=[dict(nombre='base',setup=2,mensual=0,ahorro=1,horas=3),dict(nombre='dependiente',setup=2,mensual=0,ahorro=20,horas=3,depende_de=['base']),dict(nombre='independiente',setup=3,mensual=0,ahorro=10,horas=2)]
        self.assertEqual(select_portfolio(items,4,4)['exacto']['elegidas'],['independiente'])
        self.assertEqual(select_portfolio(items,4,6)['exacto']['elegidas'],['base','dependiente'])
    def test_invalid_graph_and_inputs(self):
        for items in [[dict(nombre='a',setup=1,mensual=0,ahorro=1,depende_de=['b'])],[dict(nombre='a',setup=1,mensual=0,ahorro=1,depende_de=['a'])],[dict(nombre='a',setup=-1,mensual=0,ahorro=1)]]:
            with self.assertRaises(ValueError):select_portfolio(items,10)

class TestBenchmarkTraceability(unittest.TestCase):
    def test_keeps_all_repetitions_and_context(self):
        from types import SimpleNamespace
        from copilot.evaluator_asesor import run_benchmark_asesor
        class Runner:
            def generate_openai(self,*args):
                return SimpleNamespace(answer='RECOMENDACION: REGLAS\nUsar reglas [1].',latency_seconds=.1,cost_usd=.001,prompt_tokens=10,completion_tokens=5)
        result=run_benchmark_asesor(Runner(),[dict(id='q',q='reglas',gold='REGLAS',regla='r')],[dict(id='r',text='Usar reglas')],repeats=3,include_local=False)
        self.assertEqual(len(result['filas']['hibrido']),3)
        self.assertEqual({r['rep'] for r in result['filas']['hibrido']},{0,1,2})
        self.assertEqual(result['filas']['hibrido'][0]['contexto_ids'],['r'])
        self.assertEqual(len(result['meta']['sha256_corpus']),64)
