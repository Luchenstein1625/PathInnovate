import os
import time
from dataclasses import dataclass
from typing import Optional
from openai import OpenAI
from transformers import pipeline
import torch

@dataclass
class LLMResponse:
    provider: str
    model: str
    answer: str
    prompt_tokens: int
    completion_tokens: int
    latency_seconds: float
    cost_usd: float

class DualLLMRunner:
    def __init__(self, openai_model: str = "gpt-4o-mini", local_model_id: str = "Qwen/Qwen2.5-1.5B-Instruct"):
        self.openai_model = openai_model
        self.local_model_id = local_model_id
        
        # Cliente OpenAI
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None
        
        # Inferencia Local Hugging Face (descarga pesos la primera vez)
        print(f"Cargando modelo local {local_model_id}...")
        device = 0 if torch.cuda.is_available() else -1
        self.local_pipe = pipeline(
            "text-generation",
            model=local_model_id,
            device=device,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
        )
        print("Modelo local cargado exitosamente.")

        self.rates = {
            "openai": {"input": 0.15 / 1_000_000, "output": 0.60 / 1_000_000},
            "local": {"input": 0.0, "output": 0.0} # Costo marginal de API es cero
        }

    def generate_openai(self, prompt: str, system_prompt: str) -> LLMResponse:
        if not self.openai_client:
            raise ValueError("OPENAI_API_KEY no configurada.")
        
        t0 = time.perf_counter()
        res = self.openai_client.chat.completions.create(
            model=self.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
        latency = round(time.perf_counter() - t0, 3)
        usage = res.usage
        cost = (usage.prompt_tokens * self.rates["openai"]["input"]) + (usage.completion_tokens * self.rates["openai"]["output"])

        return LLMResponse(
            provider="OpenAI",
            model=self.openai_model,
            answer=res.choices[0].message.content or "",
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            latency_seconds=latency,
            cost_usd=round(cost, 6)
        )

    def generate_local_hf(self, prompt: str, system_prompt: str) -> LLMResponse:
        t0 = time.perf_counter()
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        outputs = self.local_pipe(messages, max_new_tokens=256, temperature=0.2)
        latency = round(time.perf_counter() - t0, 3)
        
        answer_text = outputs[0]["generated_text"][-1]["content"]
        
        # Estimación de tokens
        p_tokens = int(len(prompt.split()) * 1.3)
        c_tokens = int(len(answer_text.split()) * 1.3)

        return LLMResponse(
            provider="HuggingFace (Local)",
            model=self.local_model_id,
            answer=answer_text,
            prompt_tokens=p_tokens,
            completion_tokens=c_tokens,
            latency_seconds=latency,
            cost_usd=0.0
        )