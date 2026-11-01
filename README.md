# PathInnovate: Copiloto Académico Neuro-Simbólico

Sistema de soporte académico que combina RAG multi-proveedor, verificación lógica simbólica y optimización matemática de cronogramas.

## Arquitectura y Componentes
- **Recuperación (RAG - S1):** Búsqueda de fragmentos contextuales desde guías y syllabus.
- **Modelos Fundacionales (S1 & S6):** `copilot/llm_dual.py` permite evaluar y comparar OpenAI API vs. Hugging Face Serverless Endpoints bajo métricas de costo, tokens y latencia.
- **Verificación Simbólica (S3):** `copilot/verifier.py` valida citas existentes e integridad acíclica de dependencias.
- **Optimización y Asignación (S5):** `copilot/optimizer.py` formula la asignación de tareas como un problema de equilibrio de carga minimizando el *makespan*.
- **Evaluación y Benchmarking (S1-S5):** `copilot/evaluator.py` ejecuta baterías de prueba fijas para auditar alucinaciones y rendimiento económico.