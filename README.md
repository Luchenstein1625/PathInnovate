# Copiloto del Magíster: proyecto base para la tarea TAAI2

Herramienta de apoyo que lee la carpeta del magíster (transcripciones de clases, chats y, si los agregas,
diapositivas, PDFs, notebooks y resúmenes `.md`), la indexa y ayuda a cuatro cosas de la tarea grupal:

1. **Recordar**: buscar qué se dijo de un tema, en qué clase y en qué minuto (`ask`).
2. **Ordenar**: ver el temario de cada clase por tramos de tiempo (`outline`) y armar el borrador del Anexo A,
   la trazabilidad del syllabus (`trace`).
3. **Organizarse**: repartir las secciones y calendarizar los 14 días (`plan`).
4. **Revisar**: contrastar un borrador del informe contra los tópicos (`check`).

## Qué es y qué no es

- **No es el entregable.** El entregable es un informe PDF de evaluación de presupuesto y factibilidad. El
  enunciado dice que programar es opcional: si lo usan, sirve como evidencia en las secciones 7 y 11.
- **Es la solución que van a evaluar, en versión mínima.** Recuperador, verificador, planificador y optimizador
  de este proyecto corresponden a los componentes de la arquitectura del informe.
- **Todo uso de IA se declara en el Anexo C** (plantilla al final). Las cifras y citas que firmen son suyas.

## Dónde poner la carpeta del magíster

Descomprime `MAGISTER.zip` en la **raíz de este proyecto**, de modo que quede `magister-copilot/MAGISTER/01 ...`.
Los comandos la encuentran solos. Si la dejas en otro lugar, usa `--root "ruta"` o la variable `MAGISTER_ROOT`.
`MAGISTER/` ya está en `.gitignore`.

## Qué hay realmente en tu carpeta (verificado con el zip que subiste)

- **Son 290 archivos y todos son texto de clases** (`.txt`, `.vtt`, `.srt`, `.tsv`). No hay PDFs, PPTX, notebooks,
  syllabus ni resúmenes `.md`. Consecuencia: **las diapositivas y el syllabus de TAAI2 no están indexados**, y los
  tópicos de `config/topics.csv` no se pueden contrastar con el syllabus oficial.
- **Casi la mitad es repetido**: la misma clase aparece como `.vtt`, `.srt`, `.txt` y `.tsv`, y a veces como copia en
  una subcarpeta (por ejemplo `Clase 1 - Zoom.vtt` y `Clase 1/Clase 1 - Zoom.txt`). Con la detección por contenido
  quedan **93 archivos únicos** (137 se omiten) y 8.744 trozos de texto.
- **Los chats de Zoom** se indexan sin los nombres de quienes escriben ni las reacciones.
- **TAAI2 (carpeta 16) tiene 5 grabaciones**, asignadas a sesiones por su fecha (supuesto, ver abajo):

  | Fecha | Sesión | De qué trata, según el temario (`outline`) |
  |---|---|---|
  | 21-sep | S1 | modelos pequeños, atención, encoder/decoder, clasificación de reclamos, avatar y voz, costos, multimodal, Mamba |
  | 28-sep | S2 | agentes y workflows, grados de autonomía, aduana, fiscalizador y juez, confiabilidad punta a punta, hubs, acciones irreversibles, estado compartido |
  | 05-oct | S3 | taller de destilación (estudiante imita al profesor), entrenamiento por rondas, redes de la mosca, computación cuántica, defensa del trabajo grupal |
  | 19-oct | S4 | planificación: robots, combinaciones de acciones, planificador clásico, LLM como planificador, juez |
  | 26-oct | S5 | demo Finbot: Docker, Cloud Run, GitHub, Hugging Face, pruebas de carga con Locust |

- **Hallazgo importante: la grabación del 05-oct no es "Razonamiento simbólico y lógico".** El enunciado nombra la
  S3 así y la S5 como "Optimización", pero en las grabaciones no hay una clase dedicada a ninguna de las dos: lo
  simbólico aparece repartido en S1, S2 y S4, y optimización solo se roza en S2 y S4 (y la S5 es la demo de
  despliegue). Esos contenidos hay que cubrirlos con las diapositivas del curso (no están en el zip) y con los cursos
  de apoyo (02, 03, 15). Esto sale de leer las transcripciones: confírmenlo con el syllabus antes de decidir.
- **No hay grabación de la S6** (Economía de la IA), porque todavía no ocurre. Sus tópicos quedan marcados así.
- **Supuesto sobre las sesiones**: las fechas se asignan a S1 a S5 en orden. Está respaldado por el enunciado (el
  26-oct fue la Sesión 5, con la demo Finbot) y por el contenido de S1, S2, S4 y S5. Si el calendario es otro,
  edita `TAAI2_SESSIONS` en `copilot/defaults.py`.

## Instalación

Requiere Python 3.10 o superior (probado con 3.13).

```powershell
# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

```bash
# macOS / Linux
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Todos los comandos se ejecutan como `python -m copilot <comando>` desde la raíz del proyecto. Los CSV se guardan con
BOM para que Excel abra bien las tildes.

## Cómo continuar, paso a paso

### Paso 0: configuración inicial

```bash
python -m copilot init
```

Crea `config/topics.csv`, `config/sections.csv` y `config/team.csv`. Son los tres archivos que el grupo edita.

### Paso 1: recorrer la carpeta

```bash
python -m copilot scan
```

Imprime un resumen por curso (con los duplicados) y genera `data/inventory.csv`. **Qué revisar:** la sección
"Alertas" y las carpetas excluidas. Si algo excluido les sirve, repitan con `--include-otros` o `--include-capstone`.

### Paso 2: completar el material y ajustar el inventario

- **Agreguen a la carpeta 16 las diapositivas de TAAI2 (PDF o PPTX) y el syllabus.** Sin ellos, las sesiones S3 y S5
  quedan sin cobertura teórica en el índice.
- Abran `data/inventory.csv` y cambien `status` a `excluido` en lo que no quieran indexar, o a `indexar` en lo que sí.
- Si agregaron archivos, repitan el paso 1 (o usen `ingest --rescan`).

### Paso 3: construir el índice

```bash
python -m copilot ingest --rescan
```

Extrae el texto, lo trocea con ubicación (minuto, página, diapositiva o celda) y arma un índice BM25. Tarda unos
7 segundos con este material. **Qué revisar:** las líneas que empiezan con `!` (PDFs escaneados sin texto, archivos
vacíos, errores de lectura).

### Paso 4: hacer preguntas al material

```bash
python -m copilot ask "qué es destilación de modelos" --course 16 --session S3
python -m copilot ask "algoritmo genético mutación" -k 5
python -m copilot ask "orquestador y humano en el circuito" --prompt
```

Cada resultado trae la cita (`[curso·sesión] archivo @ minuto`) y un recorte del texto centrado en lo que buscaron.
Por defecto muestra como máximo 2 resultados por archivo (`--per-file 0` lo quita). Con `--prompt` obtienen un prompt
con las fuentes numeradas y una estimación de tokens, útil como punto de partida del costo por consulta (sección 2).

**Prueben con 5 preguntas cuya respuesta ya conozcan** antes de confiar en la búsqueda. Es búsqueda por palabras, no
por significado: con sinónimos puede no encontrar nada (ver Paso 8).

### Paso 5: ver el temario de cada clase

```bash
python -m copilot outline --course 16 --window 20
```

Genera `output/temario_16.md`: para cada grabación y cada tramo de 20 minutos, los términos que más se concentran ahí.
Sirve para ubicar "dónde se habló de X" y para **escribir las palabras clave de los tópicos con el vocabulario real del
profesor**. Son pistas para ubicarse, no un resumen: verifiquen con `ask`.

### Paso 6: reemplazar los tópicos por el syllabus real

`config/topics.csv` trae una **propuesta mía** derivada de la tabla del enunciado y ajustada con el vocabulario de las
grabaciones. No pude leer `SYLLABUS_TAAI.pdf`. Ábranlo y, para cada objetivo o contenido de S1 a S6, ajusten una fila:
sesión, id, tópico, palabras clave (separadas por `;`, en español e inglés, sin tildes da igual) y sección(es) del
informe donde se aplicará. Es el insumo del Anexo A.

### Paso 7: generar el borrador del Anexo A

```bash
python -m copilot trace
```

Genera `output/trazabilidad_borrador.csv` y `.md`. Para cada tópico indica cómo está cubierto:

| Estado | Significa |
|---|---|
| `dictado en Sx` | hay un tramo de la grabación de esa sesión con al menos 2 frases clave distintas o 3 apariciones |
| `mención débil en Sx` | aparece una palabra clave suelta en esa sesión; **no basta** como evidencia |
| `visto en otra sesión TAAI2` | está en otra grabación de TAAI2, no en la de su sesión |
| `solo cursos de apoyo` | solo aparece en cursos anteriores (02, 03, 05, 12, 15, ...) |
| `SESIÓN SIN GRABACIÓN` | la sesión no tiene grabación (hoy, la S6) |
| `SIN MATERIAL` | no aparece en ningún lado: falta subir material o hay que citar una fuente externa |

Con sus 5 grabaciones y los tópicos propuestos, `dictado en` aparece en pocos tópicos, y los de S3 y S5 salen
`visto en otra sesión`, coherente con el hallazgo de arriba. Las columnas "aplicado en informe", "página" y
"justificación si no aplica" se completan a mano cuando el informe esté escrito.

### Paso 8: repartir secciones y calendarizar

Editen `config/team.csv` (horas por día hábil y de fin de semana, fortalezas, días sin disponibilidad) y
`config/sections.csv` (horas estimadas, dependencias, día límite). Luego:

```bash
python -m copilot plan
```

Genera `output/plan_14_dias.md` y `.csv`, con responsable, apoyo, inicio, fin y alertas. Con las disponibilidades de
ejemplo (3 h por día hábil y 5 h por día de fin de semana por persona) todo cabe; **con 2 h y 4 h no cabe**. Es una
heurística voraz y las horas por sección son supuestos. Si quieren usarla como evidencia para las secciones 5 y 6,
reemplácenla por un solver (por ejemplo OR-Tools CP-SAT) y comparen ambos resultados.

### Paso 9 (opcional): conectar un LLM y mejorar la recuperación

- **Sin costo extra:** usen `ask --prompt` y peguen el resultado en un chat.
- **Con API** (requiere una clave y se paga aparte; este fragmento no lo probé):

  ```python
  import anthropic
  client = anthropic.Anthropic()   # lee ANTHROPIC_API_KEY
  msg = client.messages.create(model="claude-sonnet-5-5", max_tokens=1200,
                               messages=[{"role": "user", "content": prompt}])
  print(msg.content[0].text)
  ```
- **Búsqueda por significado:** el índice es léxico. Para sinónimos, agreguen embeddings (por ejemplo
  `sentence-transformers` con un modelo multilingüe) sobre `data/chunks.jsonl` y combinen ambos puntajes. Documenten
  el cambio: es evidencia para las secciones 2 y 11.

### Paso 10: pasar de herramienta a evidencia para el informe

| Componente del proyecto | Qué falta construir | Sección del informe |
|---|---|---|
| Recuperador (`ask`) | Síntesis con un LLM, citas obligatorias, rechazo si no hay fuente | 2, 3 |
| Verificador (`check`, `trace`) | Reglas duras: prerrequisitos, fechas, porcentajes de nota; ontología de conceptos del syllabus | 4 |
| Planificador | Modelar el proyecto como acciones con precondiciones y efectos (PDDL o HTN) y replanificar si hay atrasos | 5 |
| Optimizador (`plan`) | Formular variables, función objetivo y restricciones; comparar con un solver o una metaheurística | 6 |
| Despliegue | Contenedor y servicio en la nube (referencia: la demo Finbot del 26-oct), CI/CD, rollback | 7 |

### Paso 11: antes de entregar

```bash
python -m copilot check borrador.md     # también acepta .docx y .pdf
```

Genera `output/chequeo_borrador.md`: secciones y anexos que faltan, tópicos ausentes, solo mencionados o mencionados
fuera de su sección, y una estimación de páginas. Es un contador de frases clave: **no evalúa si un tópico está bien
aplicado a la solución**. Sirve para encontrar vacíos, no para certificar calidad. Con encabezados markdown (`#`) la
revisión por sección funciona mejor.

## Mapa de sesiones, cursos de apoyo y secciones del informe

| Sesión TAAI2 | Cursos de apoyo (inferidos de los nombres de archivo) | Sección del informe |
|---|---|---|
| S1 Modelos fundacionales (xLMs) | 07 PLN, 14 TAIA1, 09 Tópicos emergentes, 01 | 2 |
| S2 IA autónoma y sistemas complejos | 05 Agentes, 12 Simulación de agentes, 09 | 3 y 9 |
| S3 Razonamiento simbólico y lógico | 02 Representación de conocimientos | 4 |
| S4 Planificación avanzada | 03 Búsqueda y heurísticas, 05 | 5 |
| S5 Optimización (y demo Finbot) | 03 (algoritmos genéticos), 15 Bioinspirados, 04 | 6 y 7 |
| S6 Economía de la IA y estrategia | 11 Taller de diseño e innovación, 09, 01 | 8, 9 y 10 |
| Transversal | 04, 10 | 11 |

Si algún apoyo está mal asignado, se corrige en `SUPPORT` de `copilot/defaults.py`.

## Limitaciones conocidas

- **Probado con tu carpeta real, pero solo con transcripciones.** Los lectores de PDF, PPTX, DOCX y notebooks se
  probaron solo con archivos sintéticos. Cuando agreguen el material real, revisen las líneas `!` del Paso 3.
- Los **tópicos y palabras clave** son una propuesta, no el syllabus (Paso 6).
- La asignación de **fechas a sesiones** es un supuesto (ver arriba).
- Las **horas por sección** del plan y las disponibilidades son supuestos (Paso 8).
- La búsqueda es **léxica (BM25)**: no entiende sinónimos ni paráfrasis. Los errores de la transcripción automática
  ("hackingface", "grock") también afectan lo que se encuentra.
- La **detección de duplicados** se calibró con este material (copias sobre 0,29 de similitud, clases distintas bajo
  0,03, umbral 0,25). Revisen `data/inventory.csv`, columna `note`, si sospechan que se omitió una clase distinta.
- Las **transcripciones `.txt` sin tiempos** se citan por posición (`≈45%` de la clase), no por minuto. Como el
  índice conserva el `.vtt` cuando existe, esto solo ocurre si la clase no tiene versión con tiempo.
- Las **diapositivas con texto dentro de imágenes** y los PDFs escaneados no se leen (no hay OCR). Los `.xlsx`,
  imágenes y `.json` se ignoran.
- Las citas indican el inicio del fragmento (1 a 2 minutos de clase), no la frase exacta.

## Privacidad

- `data/`, `output/` y `MAGISTER/` contienen texto de sus clases y están en `.gitignore`. **No suban el proyecto con
  esos datos a un repositorio público.**
- `Otros/13 CAPSTONE` y `Otros/00 Intro/0 - Proyecto Capstone` incluyen material de un proyecto bancario y quedan
  excluidos por defecto. El enunciado permite usar un caso real si se anonimiza; no mezclen datos confidenciales en el
  informe ni en el índice compartido.
- Las transcripciones y los chats mencionan a compañeros y docentes por su nombre. Los chats se indexan sin las
  etiquetas de autor, pero el texto de los mensajes se conserva tal cual.
- Si pegan fragmentos en un chat o los envían a una API, ese texto sale de su computador. Revisen las reglas de la
  universidad y de su empresa antes de hacerlo con material que no sea de clase.

## Estructura del proyecto

```
magister-copilot/
├── README.md
├── requirements.txt
├── MAGISTER/               (tu carpeta de clases; no se sube)
├── config/                 (se crea con `init`)
├── copilot/
│   ├── defaults.py         cursos, sesiones TAAI2, tópicos, secciones y equipo por defecto
│   ├── scan.py             inventario, clasificación y detección de duplicados
│   ├── extract.py          lectores de txt, vtt/srt/tsv, md, pdf, pptx, docx e ipynb
│   ├── index.py            trozos, índice BM25, búsqueda y prompt con fuentes
│   ├── outline.py          temario por tramos de tiempo
│   ├── trace.py            Anexo A (trazabilidad) y chequeo de borradores
│   ├── planner.py          reparto y calendario de 14 días
│   ├── textutil.py         normalización y recortes de texto
│   └── cli.py              comandos
├── tests/test_smoke.py     19 pruebas sobre un árbol sintético
├── data/                   (se crea al ejecutar; no subir)
└── output/                 (se crea al ejecutar; no subir)
```

Para correr las pruebas: `python -m unittest discover -s tests -t .`

## Plantilla para el Anexo C (declaración de uso de IA)

> **Herramientas:** [Claude, ChatGPT, otras] y este proyecto base (`magister-copilot`).
> **Para qué se usaron:** [ej.: estructurar el esquema del informe, generar el código del indexador, proponer una
> tabla de trazabilidad inicial, repartir secciones].
> **Qué produjo cada herramienta y qué cambió el grupo:** [describir].
> **Cómo se verificó:** [ej.: cada cifra del presupuesto se contrastó con la fuente y la fecha de consulta del
> Anexo B; cada cita se comprobó en el material de clase; el código se probó con preguntas de respuesta conocida].
> **Lo que no se delegó:** [ej.: elección de la solución, la recomendación final y el análisis de riesgos].
