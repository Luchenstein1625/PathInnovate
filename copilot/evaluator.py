import json
from typing import List, Dict
from copilot.llm_dual import DualLLMRunner
from copilot.verifier import GroundingVerifier

def run_evaluation_benchmark(queries: List[str], mock_retriever) -> List[Dict]:
    runner = DualLLMRunner()
    results = []

    for q in queries:
        chunks = mock_retriever.retrieve(q)
        context_str = "\n".join([f"[{i+1}] {c['text']}" for i, c in enumerate(chunks)])
        system_prompt = f"Responde únicamente usando esta evidencia:\n{context_str}"

        # 1. Ejecución Alternativa A (OpenAI)
        res_openai = runner.generate_openai(q, system_prompt)
        grounded_oa, errors_oa = GroundingVerifier.verify_citations(res_openai.answer, chunks)

        # 2. Ejecución Alternativa B (Hugging Face)
        res_hf = runner.generate_huggingface(q, system_prompt)
        grounded_hf, errors_hf = GroundingVerifier.verify_citations(res_hf.answer, chunks)

        results.append({
            "query": q,
            "openai": {
                "latency_s": res_openai.latency_seconds,
                "cost_usd": res_openai.cost_usd,
                "tokens": res_openai.prompt_tokens + res_openai.completion_tokens,
                "grounded": grounded_oa,
                "errors": errors_oa
            },
            "huggingface": {
                "latency_s": res_hf.latency_seconds,
                "cost_usd": res_hf.cost_usd,
                "tokens": res_hf.prompt_tokens + res_hf.completion_tokens,
                "grounded": grounded_hf,
                "errors": errors_hf
            }
        })

    return results