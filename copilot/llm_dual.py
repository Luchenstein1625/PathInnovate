import os
import time
from dataclasses import dataclass


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
    # VERIFICAR estos precios en la pagina oficial del proveedor y registrar fecha en el Anexo B.
    RATES = {"openai": {"input": 0.15 / 1e6, "output": 0.60 / 1e6}, "local": {"input": 0.0, "output": 0.0}}

    def __init__(self, openai_model="gpt-4o-mini", local_model_id="Qwen/Qwen2.5-1.5B-Instruct", load_local=True):
        self.openai_model, self.local_model_id = openai_model, local_model_id
        self.rates = self.RATES
        self.openai_client = None
        if os.getenv("OPENAI_API_KEY"):
            from openai import OpenAI
            self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.local_pipe, self.device_label = None, "n/a"
        if load_local:
            self._load_local()

    def _load_local(self):
        import torch
        from transformers import pipeline
        cuda = torch.cuda.is_available()
        self.local_pipe = pipeline("text-generation", model=self.local_model_id, device=0 if cuda else -1,
                                   torch_dtype=torch.float16 if cuda else torch.float32)
        self.device_label = "gpu-cuda" if cuda else "cpu"
        self.local_pipe([{"role": "user", "content": "hola"}], max_new_tokens=4, do_sample=False)  # calentamiento

    @staticmethod
    def _msgs(prompt, system_prompt):
        return ([{"role": "system", "content": system_prompt}] if system_prompt else []) + [{"role": "user", "content": prompt}]

    def generate_openai(self, prompt: str, system_prompt: str = "") -> LLMResponse:
        if not self.openai_client:
            raise ValueError("OPENAI_API_KEY no configurada.")
        t0 = time.perf_counter()
        res = self.openai_client.chat.completions.create(model=self.openai_model, temperature=0,
                                                         messages=self._msgs(prompt, system_prompt))
        lat, u = round(time.perf_counter() - t0, 3), res.usage
        cost = u.prompt_tokens * self.rates["openai"]["input"] + u.completion_tokens * self.rates["openai"]["output"]
        return LLMResponse("OpenAI", self.openai_model, res.choices[0].message.content or "",
                           u.prompt_tokens, u.completion_tokens, lat, round(cost, 6))

    def generate_local_hf(self, prompt: str, system_prompt: str = "") -> LLMResponse:
        if self.local_pipe is None:
            self._load_local()
        msgs, tok = self._msgs(prompt, system_prompt), self.local_pipe.tokenizer
        t0 = time.perf_counter()
        out = self.local_pipe(msgs, max_new_tokens=256, do_sample=False)
        lat = round(time.perf_counter() - t0, 3)
        ans = out[0]["generated_text"][-1]["content"]
        ids = tok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=True)
        p = len(ids["input_ids"]) if hasattr(ids, "keys") else len(ids)       # tokens reales, no estimados
        return LLMResponse("HuggingFace (Local)", self.local_model_id, ans, p, len(tok(ans).input_ids), lat, 0.0)

    generate_huggingface = generate_local_hf  # alias: evaluator.py llamaba a este nombre y fallaba
