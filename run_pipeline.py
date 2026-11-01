import os
import sys
import json
from dotenv import load_dotenv

# Carga automáticamente las variables de tu archivo .env
load_dotenv()

from copilot.llm_dual import DualLLMRunner
from copilot.verifier import GroundingVerifier
from copilot.optimizer import WorkloadOptimizer

def main():
    print("=== INICIANDO PIPELINE COMPLETO DE PATHINNOVATE ===")

    # 1. Recuperación de contexto
    print("\n[1/4] Recuperando contexto normativo y de la guía...")
    chunks = [
        {"id": 1, "text": "La entrega final del informe es el 8 de noviembre a las 23:59 horas."},
        {"id": 2, "text": "El informe debe contener entre 20 y 35 páginas sin contar anexos."},
        {"id": 3, "text": "Se requiere comparar al menos dos alternativas: API comercial vs modelo abierto propio."}
    ]
    context_str = "\n".join([f"[{i+1}] {c['text']}" for i, c in enumerate(chunks)])
    print(f"-> {len(chunks)} fragmentos cargados.")

    # 2. Inferencia comparativa (OpenAI vs Hugging Face)
    print("\n[2/4] Ejecutando inferencia dual (OpenAI vs Hugging Face)...")
    runner = DualLLMRunner()
    user_query = "Resume la fecha límite, la extensión del informe y la regla de presupuesto obligatoria."
    system_prompt = f"Responde a la consulta citando estrictamente las fuentes [1], [2], etc.\nContexto:\n{context_str}"

    print(" -> Consultando OpenAI...")
    try:
        res_oa = runner.generate_openai(user_query, system_prompt)
        print(f"    OpenAI ({res_oa.model}): Latencia={res_oa.latency_seconds}s | Costo=${res_oa.cost_usd} USD | Tokens={res_oa.prompt_tokens + res_oa.completion_tokens}")
        print(f"    Respuesta: {res_oa.answer.strip()[:100]}...")
    except Exception as e:
        print(f"    Error OpenAI: {e}")
        res_oa = None

    print(" -> Consultando Hugging Face...")
    try:
        res_hf = runner.generate_local_hf(user_query, system_prompt)
        print(f"    HF ({res_hf.model}): Latencia={res_hf.latency_seconds}s | Costo=${res_hf.cost_usd} USD | Tokens={res_hf.prompt_tokens + res_hf.completion_tokens}")
        print(f"    Respuesta: {res_hf.answer.strip()[:100]}...")
    except Exception as e:
        print(f"    Error Hugging Face: {e}")
        res_hf = None

    # 3. Verificación Simbólica (Grounding)
    print("\n[3/4] Ejecutando Verificador Simbólico Neuro-Grounding...")
    text_to_verify = res_oa.answer if res_oa else (res_hf.answer if res_hf else "")
    if text_to_verify:
        grounded, errors = GroundingVerifier.verify_citations(text_to_verify, chunks)
        print(f" -> Citas verificadas en contexto: {'OK (Válidas)' if grounded else 'FALLÓ (Alucinación o sin citas)'}")
        if errors:
            print(f"    Detalles: {errors}")

    sample_tasks = [
        {"id": "T1", "name": "Redacción Sección 1", "duration_hours": 4.0, "depends_on": []},
        {"id": "T2", "name": "Presupuesto y TCO", "duration_hours": 6.0, "depends_on": ["T1"]},
        {"id": "T3", "name": "Revisión final", "duration_hours": 2.0, "depends_on": ["T2"]}
    ]
    is_valid_dag, msg_dag = GroundingVerifier.validate_precedence_graph(sample_tasks)
    print(f" -> Consistencia de dependencias: {msg_dag}")

    # 4. Optimización de Cronograma
    print("\n[4/4] Optimizando asignación de tareas a integrantes...")
    integrantes = {"Integrante_1": 10.0, "Integrante_2": 8.0, "Integrante_3": 12.0}
    optimizer = WorkloadOptimizer(members=integrantes)
    schedule_result = optimizer.schedule(sample_tasks)

    print(" -> Resultado de la optimización:")
    print(f"    Makespan (máxima carga en horas): {schedule_result['balanced_metric_makespan']} hrs")
    print(f"    Asignación: {json.dumps(schedule_result['schedule'], indent=6)}")
    print(f"    Tareas sin asignar: {len(schedule_result['unassigned_tasks'])}")

    print("\n=== PIPELINE FINALIZADO CON ÉXITO ===")

if __name__ == "__main__":
    main()