# PathInnovate

## Entrega actualizada con feedback y FINAL3

Los documentos vigentes están en [entrega/](entrega/LEEME.md): PDF, Word y Excel sincronizados, con cinco gráficos integrados. Consulta [la matriz de correcciones y límites](docs/APLICACION_FEEDBACK.md). El resultado permite un piloto supervisado; no autoriza escalar. Fecha: 15/11/2026, 23:59 Chile. Las identidades/aportes del grupo y la validación independiente requieren ratificación real.


Orienta a cualquier persona a **innovar con IA sin que le vendan algo más caro de lo que necesita**. Recomienda la solución más simple que resuelve su problema y se paga sola (nada de IA, reglas, ML clásico, RAG con API, modelo propio o agente), y explica por qué las alternativas más caras no hacen falta.

Además sirve de apoyo a la **Tarea grupal TAAI2** (Magíster en IA · UAI): busca en el material de las clases, arma la trazabilidad (Anexo A), calcula presupuesto (Anexo B) y revisa borradores. El PDF del informe lo escribe el grupo.

**Principio de diseño:** la decisión la toma un árbol de reglas determinista y auditable. El LLM (ChatGPT / Hugging Face) solo convierte texto libre en datos y explica; no decide y no puede subir la recomendación a algo más caro.

---

## 1. Instalación (una vez)

Requiere Python 3.11+. En PowerShell, dentro de la carpeta del proyecto:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Usa `python -m pip`, no `pip` a secas (si copiaste la carpeta, el `pip.exe` del venv puede apuntar a la ruta vieja).
Para las evaluaciones con modelos (`run_eval*.py`, `run_pipeline.py`): `python -m pip install -r requirements-eval.txt`.
El asesor y la web **no necesitan** instalar nada extra.

## 2. Configuración (`.env`)

Copia `.env.example` a `.env` y completa. **Sin comentarios en la misma línea que el valor.**

```
LLM_PROVIDER=openai,huggingface
LLM_MODEL_OPENAI=
LLM_MODEL_HUGGINGFACE=Qwen/Qwen3.5-4B
OPENAI_API_KEY=
HF_TOKEN=
MAGISTER_ROOT=
```

| Variable | Qué hace |
|---|---|
| `LLM_PROVIDER` | Cadena con respaldo: `openai,huggingface` prueba ChatGPT y, si falla, Hugging Face. También `hf_local` (modelo en tu PC con transformers) y `anthropic`. |
| `LLM_MODEL_OPENAI` | Opcional. Si está vacío usa `gpt-4o-mini`. |
| `LLM_MODEL_HUGGINGFACE` | Modelo del router de Hugging Face (debe estar disponible para tu cuenta). |
| `OPENAI_API_KEY`, `HF_TOKEN` | Tus claves. |
| `MAGISTER_ROOT` | Carpeta con las clases (por defecto `MAGISTER/` en la raíz). |

Sin claves todo funciona igual, salvo lo marcado como "LLM".

**Seguridad:** `.env` está en `.gitignore` pero **no** queda protegido si comprimes la carpeta. Borra `.env` antes de zipear o compartir. Si una clave se expuso, regenérala.

---

## 3. Asesor anti-sobreventa (el producto)

### 3.1 Por terminal

```powershell
python -m copilot recommend --tarea faq --volumen 600 --costo-caso 1.5 --preguntas-distintas 15
```
(`python -m copilot.advisor ...` es equivalente.)

| Opción | Significado |
|---|---|
| `--tarea` | `faq` (preguntas repetidas), `consulta_docs` (responder buscando en documentos), `prediccion`, `accion` (aprobar/reembolsar/ejecutar), `asignacion` (turnos, rutas, recursos) |
| `--volumen` | Casos por mes |
| `--costo-caso` | USD que cuesta hoy atender un caso a mano |
| `--preguntas-distintas` | Cuántas preguntas distintas hay (FAQ con menos de 50 ⇒ reglas, sin IA) |
| `--etiquetados` | Casos con resultado conocido (predicción: menos de 500 ⇒ reglas y recolectar datos) |
| `--recursos` | Personas/vehículos a asignar (5 o menos ⇒ planilla) |
| `--cobertura` | Fracción automatizable, 0 a 1 (por defecto 0.7) |
| `--regulado` | Normativa estricta ⇒ agrega verificador y humano |
| `--privacidad` | Los datos no pueden salir de la organización ⇒ modelo propio (si hay equipo técnico) |
| `--herramienta-existente` | Ya hay una agenda/formulario/plantilla que lo resuelve ⇒ NO_IA |
| `--pasos-variables` | Debe ejecutar acciones de varios pasos (reembolso + correo, reasignar rutas) ⇒ agente con humano que valida |
| `--lenguaje` | Además debe responder en lenguaje natural (con `accion` o `prediccion` arma la arquitectura combinada) |
| `--meses-historial` | Meses de datos históricos en planilla (12 o más ⇒ ML clásico) |
| `--sin-personal-tecnico` | No hay equipo técnico ⇒ servicio administrado (API) con acuerdo de datos, aunque haya privacidad |
| `--agente-atencion` | Agente de atención al cliente que responde con políticas o cifras ⇒ agrega verificador |
| `--texto "..."` | Describe el negocio en texto libre (con `--llm` lo convierte en datos) |
| `--llm` | Usa ChatGPT/HF para entender el texto y explicar el resultado |
| `--json` | Salida en JSON |

Ejemplos:
```powershell
# Banco: datos que no pueden salir + normativa
python -m copilot recommend --tarea consulta_docs --volumen 20000 --costo-caso 2 --regulado --privacidad
# Pocos datos para predecir
python -m copilot recommend --tarea prediccion --volumen 2000 --costo-caso 3 --etiquetados 80
# Texto libre + LLM (revisa la línea "Datos entendidos del texto")
python -m copilot recommend --texto "Tengo una panadería, me escriben 300 consultas al mes por WhatsApp con lo mismo" --costo-caso 1 --preguntas-distintas 12 --llm
```

La salida trae: recomendación, componentes, **árbol de decisión paso a paso**, costo y ahorro a 12 meses, recuperación de la inversión y cuánto **pagarías de más** por cada alternativa más cara. Si no se paga sola, responde `NO_AUTOMATIZAR_AUN`.

Los costos por peldaño son **supuestos**. Para cambiarlos crea `config/advisor_costs.json` con `{"API_RAG": [1500, 80, 0.0006]}` (instalación USD, fijo mensual USD, variable por caso USD). Verifica precios reales y fecha en el Anexo B.

### 3.2 Página única (Asesor + Benchmark)

```powershell
python -m copilot web            # abre http://127.0.0.1:8000
python -m copilot web --port 9000 --no-browser
```
Abre una sola página con dos pestañas: **Asesor anti-sobreventa** (formulario en lenguaje simple) y **Benchmark de modelos** (costos y respuestas de cada configuración, el panel de antes). Escucha solo en tu PC (127.0.0.1), así tus claves no salen. Cierra con Ctrl+C. Si marcas "Usar IA", necesita las claves del `.env`.

---

## 4. Material de las clases

Todos los comandos aceptan `--data` (por defecto `data/`), `--out` (`output/`) y `--config` (`config/`).

```powershell
python -m copilot init                     # crea config/ y carpetas base
python -m copilot scan                     # inventaria MAGISTER/ (--include-otros, --include-capstone, --max-mb, --root)
python -m copilot ingest                   # extrae texto y construye el índice (--rescan para rehacer el inventario)
python -m copilot ask "qué es destilación" -k 5
python -m copilot ask "qué es RAG" --session S1 --course 16 --per-file 1
python -m copilot ask "qué es RAG" --prompt        # imprime un prompt con fuentes para pegar en un chat
python -m copilot ask "qué es RAG" --llm           # LLM: responde usando las fuentes
python -m copilot outline --course 16 --window 15 --top 8   # temario por tramos de tiempo
```
`ask` filtra por `--course`, `--session S1..S5`, `--kind` (transcript, chat, slides...), `-k` (resultados) y `--per-file`. Cada fragmento trae clase y minuto.

## 5. Informe de la tarea

```powershell
python -m copilot trace                    # borrador del Anexo A (output/trazabilidad_borrador.md/.csv)
python -m copilot check borrador.docx      # qué temas del syllabus cubre un borrador (.md .txt .docx .pdf)
python -m copilot plan                     # calendario de 14 días (output/plan_14_dias.md/.csv), según config/
```
Edita `config/team.csv` (horas y fortalezas), `config/sections.csv` (secciones y tiempos) y `config/topics.csv` (syllabus) antes de `plan` y `trace`.

## 6. De una idea a una propuesta técnica (`innovate`)

```powershell
python -m copilot innovate "asistente que atienda reclamos y asigne casos a ejecutivos" --queries 50000
python -m copilot innovate "su idea" --llm        # LLM: agrega una crítica
```
Elige componentes por reglas sobre el texto, cita evidencia de las clases (o marca `SIN EVIDENCIA`), compara tres presupuestos y escribe `output/innovacion.md`. Requiere haber hecho `ingest` para citar clases.

## 7. Cálculos de la tarea (`engine_taai2`)

```powershell
python -m copilot.engine_taai2 budget --queries 50000 --strategy all --xlsx Anexo_B.xlsx   # TCO 12/36 meses, VAN, sensibilidad
python -m copilot.engine_taai2 budget --queries 50000 --strategy api                      # api | slm_self_hosted | hybrid | all
python -m copilot.engine_taai2 reliability --acc 0.95,0.9,0.92 --hitl 2:0.8              # precisión del flujo completo
python -m copilot.engine_taai2 risks                                                      # matriz de riesgos
python -m copilot.engine_taai2 portfolio --presupuesto 12000 --horas 70 --json docs/portafolio_candidatas.json
python -m copilot.engine_taai2 optimize --agents 3 --durations 5,3,8,2,7,4,6,1            # reparto de tareas (greedy vs recocido)
python -m copilot.engine_taai2 plan "meta del proyecto"                                   # plan neuro-simbólico
python -m copilot.engine_taai2 traceability > Anexo_A.md
python -m copilot.engine_taai2 check-pdf TAAI2_Tarea_Grupo-N.pdf                          # revisa el PDF final
```

## 8. Evaluación y panel de resultados

Requiere `requirements-eval.txt` y `OPENAI_API_KEY`. Sin `--skip-local` descarga y corre un modelo local (Qwen 1.5B; lento sin GPU).

```powershell
python run_eval.py --repeats 3 --skip-local            # reglas de la tarea -> eval/resultados.json, resultados.js, Anexo_B.xlsx
python run_eval_asesor.py --repeats 3 --skip-local     # dominio del asesor -> eval_asesor/resultados_asesor.json/.js
python run_eval_asesor.py --preguntas eval_asesor/preguntas_externas.json --salida eval_asesor/externas   # otro conjunto, sin pisar lo anterior
python run_eval_motor.py                              # agrega la 6a config "Motor de reglas (asesor)" al benchmark del asesor (extractor OpenAI + árbol de decisión)
python run_eval_motor.py --sin-llm                    # igual, solo con palabras clave (costo 0; es el piso, muy pobre)
python run_eval_motor.py --preguntas eval_asesor/preguntas_externas.json --base eval_asesor/externas/resultados_asesor.json   # prueba justa: preguntas que las reglas no vieron
python run_pipeline.py                                 # demo de punta a punta (OpenAI vs Hugging Face + verificador + plan)
```
`run_eval_motor.py` **no repite** las otras 5 configuraciones: lee el resultado ya medido (`resultados_asesor.json`, o el `.js` si no hay `.json`), agrega `motor_reglas` y reescribe ambos archivos. Si no entiende de qué trata la pregunta, se abstiene en vez de adivinar. Las reglas del motor y las etiquetas de referencia las definió el mismo grupo, así que la comparación honesta es la del conjunto externo.

`run_pipeline.py` usa `python-dotenv` (ya en `requirements-eval.txt`) y carga el modelo local de Hugging Face.

**Panel (pestaña Benchmark):** se ve en `http://127.0.0.1:8000` con `python -m copilot web`, o abriendo `index.html` con doble clic (en ese modo la pestaña Asesor no funciona; necesita internet por las librerías de gráficos). Lee `resultados.js` y `eval_asesor/resultados_asesor.js`; si no existen muestra textos de ejemplo y lo avisa. Tiene un selector entre el benchmark de la tarea (5 configuraciones) y el del asesor (6: se suma el motor de reglas tras `run_eval_motor.py`).

## 9. Pruebas

```powershell
python -m unittest discover -s tests -t .
```

## 10. Qué hay en cada carpeta

| Ruta | Contenido |
|---|---|
| `copilot/advisor.py`, `asesor_llm.py`, `web.py`, `llm.py` | Asesor, capa LLM, interfaz web, conexión a ChatGPT/Hugging Face |
| `copilot/engine_taai2.py`, `budget_extras.py`, `innovate.py`, `planner.py`, `optimizer.py`, `verifier.py` | Presupuesto, riesgos, propuesta, planificación, optimización, verificador simbólico |
| `copilot/scan.py`, `extract.py`, `index.py`, `outline.py`, `trace.py`, `cli.py` | Material de las clases e interfaz de comandos |
| `index.html` | Página única: pestaña Asesor + pestaña Benchmark de modelos |
| `config/` | `team.csv`, `sections.csv`, `topics.csv`, `advisor_costs.json` (opcional) |
| `copilot/motor_asesor.py`, `run_eval_motor.py` | Mide el motor de reglas con las mismas preguntas y métricas que los LLM |
| `eval/`, `eval_asesor/` | Preguntas, corpus y resultados de los benchmarks |
| `MAGISTER/` | Transcripciones y chats de las clases (entrada de `scan`/`ingest`) |
| `data/`, `output/` | Índice de búsqueda y salidas generadas |
| `entrega/Anexo_B_PathInnovate.xlsx` | Presupuesto vigente del informe; los otros anexos son históricos |

## 11. Problemas comunes

| Síntoma | Causa y solución |
|---|---|
| `HTTP 400 de openai (modelo=...)` | El modelo no existe en tu cuenta. Define `LLM_MODEL_OPENAI` o déjalo vacío (usa `gpt-4o-mini`). |
| `HTTP 400 de huggingface` | El modelo no está disponible en el router para tu cuenta. Prueba otro en `LLM_MODEL_HUGGINGFACE` o usa solo `LLM_PROVIDER=openai`. El mensaje trae el detalle del proveedor. |
| El LLM falla | El asesor sigue funcionando por reglas y lo avisa con `!`; la recomendación no depende del LLM. |
| `Define LLM_PROVIDER` | Falta la línea en `.env` o tiene un comentario pegado en la misma línea. |
| `ask` no devuelve nada | Falta `python -m copilot ingest`. |
| `ModuleNotFoundError: dotenv` | `python -m pip install -r requirements-eval.txt`. |
| El LLM clasificó mal tu texto | Revisa la línea "Datos entendidos del texto" y pasa los datos clave por flags (tienen prioridad). |
