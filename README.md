# PathInnovate · Magister Copilot

Herramienta de línea de comandos para la **Tarea grupal TAAI2** (Máster en IA · UAI · Tópicos Avanzados en IA 2). Hace dos cosas:

1. **Apoyo al informe:** busca en el material de las clases, arma la tabla de trazabilidad (Anexo A), calcula presupuesto y sensibilidad (Anexo B), planifica el trabajo del grupo y revisa un borrador.
2. **Asesor anti-sobreventa:** a partir de una idea o del perfil de un negocio, recomienda la automatización **más simple que alcanza** (bot de reglas, RAG, ML clásico, neurosimbólico, agente, SLM propio) y avisa cuándo algo más caro no se justifica.

> El PDF del informe **no se genera aquí**: lo escribe el grupo. Este proyecto entrega números, tablas y evidencia para pegar en él.

---

## 1. Instalación

Requiere Python 3.11 o superior.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Usa `python -m pip` y no `pip` a secas: si copiaste la carpeta, el `pip.exe` del venv puede apuntar a la ruta antigua y fallar.

Solo para la evaluación con GPU (`run_eval*.py`):

```powershell
python -m pip install -r requirements-eval.txt
```

## 2. Configuración

| Qué | Dónde | Para qué |
|---|---|---|
| Carpeta del magíster | `MAGISTER/` en la raíz, o `MAGISTER_ROOT` en `.env`, o `--root` | Material de las clases (transcripciones, chats, PDF, PPTX) |
| Claves de LLM (opcional) | `.env` (copia `.env.example`) | Solo para `--llm` y `run_eval*.py` |
| Temario del syllabus | `config/topics.csv` | Temas S1 a S6, palabras clave y sección del informe |
| Secciones y tiempos | `config/sections.csv` | Entrada de `plan` |
| Equipo | `config/team.csv` | Horas y fortalezas por integrante (entrada de `plan`) |

Variables de `.env`:

```
MAGISTER_ROOT=
LLM_PROVIDER=openai        # openai | huggingface | anthropic
LLM_MODEL=                 # obligatorio, según la documentación del proveedor
OPENAI_API_KEY=
HF_TOKEN=
ANTHROPIC_API_KEY=
```

**Seguridad:** `.env` está en `.gitignore`, pero **no** queda protegido si comprimes la carpeta en un zip. Antes de compartir o subir el proyecto, borra el `.env` del zip. Si una clave se expuso, regenérala.

## 3. Flujo rápido

```powershell
python -m copilot init                 # crea config/ y carpetas
python -m copilot scan                 # inventaria el material
python -m copilot ingest               # construye el índice de búsqueda
python -m copilot ask "qué es destilación" -k 5
python -m copilot innovate "asistente que atienda reclamos y asigne casos a ejecutivos"
python -m copilot recommend --tarea consulta_docs --volumen 3000 --costo-caso 2
python -m copilot.engine_taai2 budget --xlsx Anexo_B.xlsx
python -m unittest discover -s tests -t .
```

## 4. Comandos

Todos aceptan `--data` (por defecto `data/`), `--out` (`output/`) y `--config` (`config/`).

### Material de las clases
| Comando | Qué hace |
|---|---|
| `init` | Crea la configuración y las carpetas base |
| `scan` | Recorre `MAGISTER/` y escribe el inventario (`--include-otros`, `--include-capstone`, `--max-mb`) |
| `ingest` | Extrae texto y construye el índice (`--rescan` rehace el inventario) |
| `ask "pregunta"` | Busca fragmentos con clase y minuto. Filtros: `--course`, `--session S1..S5`, `--kind`, `-k`, `--per-file`. `--prompt` imprime un prompt con fuentes para pegarlo en un chat. `--llm` responde con el modelo del `.env` |
| `outline --course 16` | Temario de la clase por tramos de tiempo (`--window`, `--top`) |

### Informe de la tarea
| Comando | Qué hace |
|---|---|
| `trace` | Borrador del Anexo A: cada tema del syllabus con sus apariciones en las clases |
| `check borrador.docx` | Revisa qué temas del syllabus cubre un borrador (`.md`, `.txt`, `.docx` o `.pdf`) |
| `plan` | Calendario de 14 días con reparto de secciones según `config/` |

### Propuesta de solución
| Comando | Qué hace |
|---|---|
| `innovate "idea"` | Elige componentes y técnicas **por reglas sobre el texto** (texto → SLM/LLM + RAG; datos tabulares → Random Forest/Boosting; asignación → optimización; normas → verificador simbólico; procesos → planificador), cita evidencia de las clases o marca `SIN EVIDENCIA`, y compara tres presupuestos. `--queries` fija las consultas mensuales; `--llm` agrega una crítica del modelo |
| `recommend --tarea … --volumen …` | Recorre la escalera de lo simple a lo caro y elige el peldaño más simple que resuelve el problema y se paga solo. `--tarea`: `faq`, `consulta_docs`, `prediccion`, `accion`, `asignacion`. Opciones: `--costo-caso`, `--etiquetados`, `--regulado`, `--privacidad` |

### Cálculos (módulo `engine_taai2`)
```powershell
python -m copilot.engine_taai2 budget --queries 50000 --strategy all --xlsx Anexo_B.xlsx
python -m copilot.engine_taai2 reliability --acc 0.95,0.9,0.92 --hitl 2:0.8
python -m copilot.engine_taai2 risks
python -m copilot.engine_taai2 optimize --agents 3 --durations 5,3,8,2,7,4,6,1
python -m copilot.engine_taai2 plan "meta del proyecto"
python -m copilot.engine_taai2 traceability > Anexo_A.md
python -m copilot.engine_taai2 check-pdf TAAI2_Tarea_Grupo-N_Apellidos.pdf
```

### Evaluación (requiere clave de OpenAI y, sin `--skip-local`, GPU)
```powershell
python run_eval.py --repeats 3              # reglas de la tarea
python run_eval_asesor.py --repeats 3       # dominio del asesor (necesita eval_asesor/preguntas.json y corpus.json)
```
Agrega `--skip-local` para omitir el modelo local (Qwen). Abre `index.html` en el navegador para ver los resultados.

## 5. Cómo funciona

```
 MAGISTER/ (clases)            idea o perfil del negocio
      │ scan + ingest                │
      ▼                              ▼
 data/index.json  ──búsqueda──▶  innovate / recommend / ask
 (BM25 por clase y minuto)            │
                                      ▼
                   reglas  →  presupuesto  →  verificador  →  salida .md
```

| Módulo | Función | Sesión |
|---|---|---|
| `extract.py`, `scan.py`, `index.py`, `textutil.py` | Lee las clases, las parte en fragmentos y busca por palabras (BM25), citando archivo y minuto | S1 |
| `llm.py`, `llm_dual.py` | Conexión opcional a OpenAI, Hugging Face o Anthropic; comparación de API contra modelo local | S1, S6 |
| `verifier.py` | Verifica citas existentes y que las dependencias no tengan ciclos | S3 |
| `engine_taai2.py` | Presupuesto (TCO, VAN, equilibrio, sensibilidad, Excel), confiabilidad de la cadena, riesgos, plan STRIPS, optimización por recocido simulado, Anexo A, chequeo de PDF | S2 a S6 |
| `optimizer.py`, `planner.py` | Reparto de tareas del equipo minimizando el makespan; calendario de 14 días | S4, S5 |
| `innovate.py`, `advisor.py` | Propuesta de técnicas por idea y escalera de recomendación con chequeo económico | S1 a S6 |
| `evaluator.py`, `evaluator_asesor.py`, `budget_extras.py` | Benchmark con preguntas fijas, métricas de alucinación y costo, y complementos de presupuesto | S1 a S6 |
| `trace.py`, `outline.py` | Anexo A y temarios por tramos | Todas |

Las recomendaciones de `innovate` y `recommend` son **reglas escritas por el equipo**, no un modelo entrenado: son un punto de partida que el grupo debe justificar.

## 6. Archivos que usa (entradas)

| Archivo o carpeta | Lo usa |
|---|---|
| `MAGISTER/` | `scan`, `ingest` |
| `config/topics.csv` | `trace`, `check`, `traceability`, `innovate` |
| `config/sections.csv`, `config/team.csv` | `plan` |
| `.env` | `--llm`, `run_eval*.py` |
| Borrador del informe (`.md`, `.txt`, `.docx`, `.pdf`) | `check`, `check-pdf` |
| `eval/preguntas*.json`, `eval/corpus.json` | `run_eval.py` |
| `eval_asesor/preguntas.json`, `eval_asesor/corpus.json` | `run_eval_asesor.py` |

## 7. Archivos que genera (salidas)

| Archivo | Lo genera | Va en el informe |
|---|---|---|
| `data/inventory.csv` | `scan` | — |
| `data/chunks.jsonl`, `data/index.json`, `data/meta.json` | `ingest` | — |
| `output/trazabilidad_borrador.md` y `.csv` | `trace` | Anexo A |
| `output/temario_<curso>.md` | `outline` | Apoyo |
| `output/chequeo_borrador.md` | `check` | Revisión previa a entregar |
| `output/plan_14_dias.md` y `.csv` | `plan` | Organización del grupo |
| `output/innovacion.md` | `innovate` | Secciones 2 a 6, 8 y 12 (borrador) |
| `output/recomendacion.md` | `recommend` | Secciones 10 y 12 |
| `Anexo_B.xlsx` (hojas Supuestos, TCO, Sensibilidad) | `engine_taai2 budget --xlsx`, `run_eval.py` | Anexo B |
| `eval/resultados.json` y `resultados.js` | `run_eval.py` | Sección 11 |
| `eval_asesor/resultados_asesor.json`, `.js` y `Anexo_B.xlsx` | `run_eval_asesor.py` | Sección 11 |

Las carpetas `data/`, `output/`, `MAGISTER/` y `.venv/` están en `.gitignore`: el material del curso no se sube al repositorio.

## 8. Qué queda fuera

- **El informe PDF** de 20 a 35 páginas, la recomendación, los riesgos adaptados a su solución y los Anexos C (uso de IA) y D (aportes por integrante).
- **Cifras reales:** precios, costos de personal, CAPEX y tasa de descuento son supuestos hasta que el grupo los respalde con fuentes y fecha en el Anexo B.
- **Declaración de IA:** si usan `--llm` o cualquier asistente, va en el Anexo C. Lo que firman es del grupo, incluidas las cifras y las citas.

## 9. Pruebas

```powershell
python -m unittest discover -s tests -t .
```
