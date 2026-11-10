# Mejoras PathInnovate — copiar encima del proyecto
- copilot/advisor.py   NUEVO  asesor anti-sobreventa (comando `recommend` que el README promete y no existia)
- copilot/asesor_llm.py NUEVO capa LLM (ChatGPT/HF): texto libre -> datos, y explicacion. No decide.
- copilot/llm.py       REEMPLAZA  arregla .env con comentarios en linea; cadena openai,huggingface; hf_local
- tests/test_advisor.py NUEVO
- .env.example         REEMPLAZA
Uso: python -m copilot.advisor --tarea faq --volumen 600 --costo-caso 1.5 --preguntas-distintas 15
     python -m copilot.advisor --texto "..." --costo-caso 1 --llm
Antes de nada: REGENERA las claves OpenAI y HF (iban dentro del zip en .env) y borra .env de cualquier zip.
