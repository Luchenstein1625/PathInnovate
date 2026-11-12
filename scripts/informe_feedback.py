"""Actualiza el informe existente con evidencia, presupuesto y figuras vigentes."""
from pathlib import Path
from copy import deepcopy
import json,re
from docx import Document
from docx.shared import Pt,Inches,RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from openpyxl import load_workbook
ROOT=Path(__file__).resolve().parents[1]
d=Document(ROOT/'docs/templates/informe_base.docx');ps=list(d.paragraphs);ts=list(d.tables)
w=load_workbook(ROOT/'entrega/Anexo_B_PathInnovate.xlsx',data_only=True)
internal=json.loads((ROOT/'eval_asesor/resultados_asesor_FINAL3.json').read_text());external=json.loads((ROOT/'eval_asesor/externas/resultados_asesor.json').read_text())
m=internal['configs']['hibrido']['metricas']; ev=json.loads((ROOT/'docs/evidencia_feedback.json').read_text())
def num(x):return f'{x:,.0f}'.replace(',','.')
def setp(i,t):ps[i].text=t
def after(i,text,style=None):
 e=OxmlElement('w:p');ps[i]._p.addnext(e);p=Paragraph(e,ps[i]._parent);p.text=text
 if style:p.style=style
 return p
def image_after(i,fn,caption):
 cap=after(i,caption);p=after(i,'');p.add_run().add_picture(str(ROOT/'entrega/figuras'/fn),width=Inches(6.4));p.paragraph_format.keep_with_next=True
 cap.paragraph_format.space_after=Pt(10)
def table_rows(t,rows):
 while len(t.rows)>1:t._tbl.remove(t.rows[-1]._tr)
 for vals in rows:
  cells=t.add_row().cells
  for c,v in zip(cells,vals):c.text=str(v)

changes={
1:'Evaluación de presupuesto y factibilidad de PathInnovate. TAAI2, UAI. Actualización al 12 de noviembre de 2026. Caso empresarial ficticio; resultados experimentales medidos y supuestos económicos identificados por separado. Entrega prorrogada: domingo 15/11/2026 a las 23:59, hora de Chile, según el feedback de revisión recibido.',
5:f'Presupuesto base: 50.000 consultas al mes. Se recomienda API + RAG + verificador para un piloto supervisado. CAPEX total: 7.500 USD; OPEX: {w["TCO"]["B7"].value:.2f} USD/mes; TCO a 12 meses: {num(w["TCO"]["B12"].value)} USD; a 36 meses: {num(w["TCO"]["B13"].value)} USD; VAN a 36 meses: {num(w["TCO"]["B17"].value)} USD; recuperación simple: mes 2. Son proyecciones condicionadas al beneficio, no retornos realizados. El beneficio supuesto es de 10.000 USD mensuales y no demuestra ahorro de caja.',
6:'Evidencia medida. FINAL3, del 12/11/2026: 32 preguntas y tres repeticiones por configuración. API + RAG + verificador: 78/96 correctas (81,2 % reportado), 0/87 sobredimensionadas, 15,6 % de abstención, p95 de 3,591 s y costo medio registrado de 0,000112 USD. En las 31 preguntas externas de la corrida histórica: 25/31 correctas y 2/27 sobredimensionadas (7,4 %). El umbral de sobredimensión ≤5 % no se cumple externamente; la latencia interna y la abstención también exceden sus metas. No se autoriza escalar.',
9:'Recomendaciones erróneas o abstenciones. No se observaron cifras sin respaldo según el control automático en la configuración API verificada de estos conjuntos. Esto no garantiza veracidad semántica ni ausencia de alucinaciones. La derivación humana requiere dimensionamiento antes del lanzamiento.',
18:'Proceso manual de referencia (supuesto): tres minutos por consulta a 8 USD por hora equivalen a 0,40 USD por atención. Con 50.000 consultas, el costo de esfuerzo es 20.000 USD/mes. Automatizar la mitad liberaría 1.250 horas y un valor bruto de 10.000 USD/mes. El ahorro solo se realiza si esas horas se eliminan o se reasignan a trabajo útil sin costos adicionales superiores al beneficio. La revisión de casos está presupuestada como incremento y debe evitarse contarla dos veces si ya pertenece a la dotación base.',
19:'El costo de recomendar una tecnología excesiva se mide aquí como frecuencia de sobredimensión, no como pérdida monetaria demostrada del cliente. FINAL3 observa 9/87 casos (10,3 %) para LLM solo y 0/87 para API verificada. No se monetiza esta diferencia sin contratos, costos de implementación y una referencia independiente.',
22:'Para cada recomendación se ofrecen costos hipotéticos y alertas. El verificador comprueba referencias y coincidencia de cifras, pero no demuestra que cada afirmación sea verdadera. El árbol determinista del producto y el benchmark generativo son rutas distintas: las métricas del benchmark no certifican el desempeño de toda la interfaz del asesor.',
30:'1.7 Hipótesis de negocio y límites de evidencia',
31:'50.000 consultas mensuales y 25 consultores describen una organización ficticia. No representan demanda observada ni un contrato comercial.',
32:'El costo manual de 0,40 USD deriva de minutos y tarifa; el 50 % de automatización es una hipótesis de inversión. Se someterán a medición en el piloto.',
33:'Remuneraciones, GPU, CAPEX y tasa de descuento son hipótesis explícitas. Se desglosan roles, dedicación y líneas de costo en el Excel; no se presentan como cotizaciones de mercado.',
34:'Las etiquetas fueron definidas por el grupo y no se dispone de validación independiente. Este límite restringe la recomendación a experimentar bajo supervisión.',
38:'La función retrieve de copilot/evaluator.py usa coincidencia léxica: cuenta la intersección de términos normalizados con cada regla y recupera top-5; no es BM25 ni utiliza embeddings. El índice general de clases sí tiene BM25, pero no debe confundirse con el recuperador del benchmark. El LLM usa representaciones distribuidas aprendidas; el corpus y las restricciones son simbólicos. Embeddings multilingües podrían mejorar paráfrasis, pero aún no se midió ese cambio.',
42:'Ajuste fino y destilación no se ejecutaron en esta iniciativa. Se evalúa un Qwen preentrenado con contexto, sin afirmar que sea un modelo entrenado por el grupo. El CAPEX de 15.000 USD para la alternativa propia es una reserva de ingeniería hipotética, no costo de entrenamiento medido.',
44:'FINAL3 registra 522,7 tokens de entrada y 55,3 de salida en promedio para API + RAG + verificador, incluyendo las llamadas registradas. La referencia del modelo indica 128.000 tokens de contexto [R1]. El tamaño observado cabe holgadamente; el control futuro debe limitar la suma de sistema, pregunta, fragmentos y salida antes de invocar el modelo. Con 21 reglas, incluir todo el corpus sería una alternativa razonable aún no comparada.',
45:'La base presupuestaria única es (522,7 × 0,15 + 55,3 × 0,60) / 1.000.000 = 0,000111585 USD/consulta. A 50.000 consultas son 5,57925 USD/mes. El JSON redondea el costo medio a 0,000112 USD; la diferencia se debe al redondeo de mediciones, no a otra tarifa. No se extrapolan los tokens de la corrida FINAL2.',
46:'Precios de entrada/salida: 0,15/0,60 USD por millón de tokens para gpt-4o-mini [R1], consultados el 12/11/2026. La inferencia local no tiene factura por API, pero su TCO incluye recursos dedicados y operación. Todos los cálculos finales se encuentran en entrega/Anexo_B_PathInnovate.xlsx.',
49:'La arquitectura experimental es un workflow de generación con herramientas y controles. La interfaz comercial añade extracción de datos y decisión por árbol; se requiere evaluación integral antes de atribuirle las métricas del benchmark. No hay negociación multiagente ni una planificación autónoma abierta. La autonomía consiste en proponer, calcular, reparar sintácticamente y abstenerse con derivación.',
53:'Gobernanza propuesta para Camino Digital: el Líder de IA es dueño del corpus y aprueba cada cambio; Calidad mantiene preguntas de regresión y revisa el 100 % de reglas modificadas; el Arquitecto valida integración; Seguridad audita accesos mensualmente; Legal revisa cambios normativos y el contrato de datos. Un consultor senior revisa semanalmente una muestra del 10 % de casos del piloto y todos los casos sensibles. El corpus se revisa trimestralmente y ante cambios de precio o normativa. Cada versión conserva autor, motivo, fecha, evidencia y resultado de pruebas. Son responsabilidades del diseño, no nombramientos ya ejecutados.',
55:'La confiabilidad del flujo se mide con eventos condicionados: P(A∩B∩C∩D)=P(A)P(B|A)P(C|A,B)P(D|A,B,C). Multiplicar precisiones marginales exige supuestos que aquí no se justifican. Por ello se reemplaza el ejemplo ilustrativo por conteos conjuntos de respuestas archivadas de la repetición 0.',
56:'En FINAL3 las 32 respuestas archivadas del híbrido cumplen formato, controles sintácticos de citas y cifras; 26 coinciden con la etiqueta. La tasa conjunta es 26/32=81,25 %. Externamente se obtiene 25/31=80,65 %. Este diagnóstico no reconstruye las 96 respuestas individuales: el JSON solo conserva la repetición 0 por pregunta; los agregados sí cubren tres repeticiones.',
57:'El recall de regla top-5 interno publicado es 1,0 para las preguntas con regla de referencia. No se mide externamente y no puede incorporarse como una etapa externa de precisión 100 %. Las abstenciones se aceptan por el control sintáctico; la coincidencia con la etiqueta se mide por separado. La detección humana de errores no fue medida y no se usa para inflar la confiabilidad. Cálculo reproducible: scripts/evidence_feedback.py.',
63:'Cifras: se comprueba si los números aparecen en algún fragmento recuperado o en la pregunta. No se comprueba por sí sola la relación semántica ni que el fragmento citado contenga la cifra.',
65:'El módulo SymbolicVerifier también contiene reglas de presupuesto, latencia, intervención humana y anonimización para propuestas estructuradas. Son controles disponibles en código; no se les atribuye ejecución automática en todas las rutas del producto. El despliegue deberá conectarlos con la política de cada acción.',
68:'Las reglas son predicados y decisiones proposicionales sobre campos estructurados. No hay ontología formal ni motor de lógica de primer orden. Para este corpus reducido se priorizan reglas editables y pruebas; una ontología tendría costo de mantenimiento sin beneficio medido. La escalera es una ayuda conceptual: ML tabular y RAG responden a problemas diferentes y no tienen un orden universal de costo.',
70:'FINAL3 no observa cifras sin respaldo mediante la métrica automática en RAG OpenAI ni en el híbrido. Por tanto, esta corrida no demuestra una reducción de 17,7 % a 0 %: esa diferencia pertenecía a FINAL2. El cambio de código o condiciones entre corridas impide atribuir la mejora a un componente aislado. El verificador sí aumenta citas sintácticamente válidas de 96,9 % a 100 % y mantiene 81,2 % de aciertos internos.',
74:'La decisión real de esta versión no requiere buscar entre planes abiertos: clasificar, recuperar, generar y verificar conforman un workflow fijo con ramificaciones de reparación y abstención. Reconocemos este alcance en lugar de presentar la secuencia como prueba de planificación avanzada. La guía permite justificar que la solución no planifica; STRIPS se conserva como demostración didáctica separada.',
75:'El ejemplo STRIPS del repositorio modela precondiciones y efectos y usa búsqueda en anchura para encontrar una secuencia. No hay evidencia de que la interfaz lo invoque para cada consulta ni de que explore planes alternativos de implementación del negocio. La acción didáctica ejecutar tampoco habilita contratación o ejecución real. No se justifica introducir PDDL o HTN para este flujo lineal.',
77:'Una verificación fallida activa reparación, un reintento o abstención: es recuperación controlada de fallos, no replanificación general. En FINAL3, API verificada reporta 4,2 % de respuestas reparadas y 0 % de reintentos; el verificador local reporta 100 % de reparaciones y 6,2 % de reintentos. La reparación añade citas por coincidencia léxica; no constituye validación semántica.',
79:'El orquestador aplica transiciones predefinidas; el LLM redacta y el verificador bloquea formatos, referencias o cifras incompatibles. El humano decide si adopta la recomendación. Una futura planificación de implementación podría elegir entre recopilar datos, preparar reglas o desplegar RAG, pero no se declara implementada.',
80:'La comparación entre un LLM que planifica solo y un planificador simbólico no se realizó. Se declara fuera del alcance experimental actual. Si se amplía el producto, se fijarán estados, acciones alternativas, metas y restricciones, y se evaluarán planes válidos, costo y pasos omitidos con un conjunto reservado. No se adjudica a esta comparación ningún resultado medido.',
89:'Se implementa enumeración exacta hasta 20 candidatas, comparada con una heurística voraz que incluye el cierre de dependencias. Para mayor tamaño se debe elegir y evaluar un solver o una metaheurística antes de ampliar ese límite. El recocido simulado existente resuelve reparto de carga; no se presenta como experimento de portafolio. La IA generativa puede proponer candidatas y explicar soluciones, pero los costos, horas y dependencias requieren aprobación humana.',
90:'El portafolio usa variables binarias xi; maximiza Σ(ahorro mensual_i − costo mensual_i)xi, sujeto a Σsetup_i xi ≤ B, Σhoras_i xi ≤ H y xi ≤ xj si i depende de j. Son horas totales de implementación, no un calendario ni makespan. Las entradas y ahorros son ilustrativos; el algoritmo verifica factibilidad y no demuestra que esos ahorros ocurrirán.',
91:'La función select_portfolio en copilot/engine_taai2.py valida nombres, costos, dependencias desconocidas y ciclos; limita el espacio a 2^20 subconjuntos. El comando portfolio acepta --presupuesto, --horas y un JSON con las candidatas. En el ejemplo de seis opciones, con presupuesto 12.000 USD sin límite de horas, el exacto obtiene 3.180 USD/mes netos frente a 2.580 del voraz. Se incluye además un caso con horas y dependencia en la evidencia reproducible.',
93:'El tiempo del portafolio se mide con perf_counter sobre un caso de seis candidatas y se guarda en docs/portafolio_feedback.json. Es tiempo de CPU del entorno de revisión, no una medición en Cloud Run. Su costo se absorbe en la infraestructura base presupuestada. El límite de 20 candidatas evita crecimiento exponencial sin control; no se promete tiempo de respuesta para tamaños no ensayados.',
98:'Objetivo de latencia del piloto: p95 ≤3 s. FINAL3 registra 3,591 s para API verificada y 12,387 s para Qwen verificado en GPU local. Ambos exceden ese objetivo; la latencia observada incluye generación y reintentos, no una prueba de carga del servicio Cloud Run. La alternativa local no se considera sustituto en línea equivalente sin nueva validación.',
99:'Diseño de estado: corpus y configuración con versión; solicitudes independientes y bitácora externa con identificador de correlación. La implementación local y el benchmark no prueban sincronización distribuida, escalado, cuotas ni rollback real. Pruebas de carga y operación pertenecen al piloto.',
100:'Cloud Run, Secret Manager, Artifact Registry y GitHub Actions son una arquitectura propuesta. La guía no exige desplegar el prototipo; no se afirma una URL operativa ni un rollback ejecutado. Antes de invertir se verificará la configuración contra documentación oficial [R2]. La alternativa GPU dedicada presupone reserva mensual; no se mezcla con el costo de un servicio CPU que escala a cero.',
103:'El cruce algebraico de OPEX entre API y SLM dedicado, manteniendo constantes personal y capacidad, es (6.601−2.650)/0,000111585 ≈35,41 millones de consultas/mes. No demuestra viabilidad a esa escala: no se ha medido capacidad concurrente ni cuántas GPU o consultores requeriría. Las alternativas tampoco tienen calidad equivalente; el SLM verificado logra 68,8 % interno frente a 81,2 % API. La decisión se basa en el escenario de 50.000 consultas, no en ese cruce extrapolado.',
105:'La sensibilidad del TCO muestra que personal domina costos. Para decidir inversión se analiza también el VAN: costo manual, automatización y volumen dominan el beneficio. En el caso API, variar ±30 % el costo por caso o la automatización mueve el VAN aproximadamente 187.119 USD entre extremos; variar personal lo mueve 47.715 USD. El escenario de tokens divididos por diez reduce el TCO API aproximadamente 181 USD (0,18 %); no prueba una tendencia futura de precios.',
107:'8.4 Interpretación y controles del presupuesto',
108:'Personal API: ingeniero IA 0,30 FTE ×5.000 USD + DevOps 0,10×4.500 + consultor 0,20×3.000 =2.550 USD/mes. Mixto: 4.000; SLM: 5.575. Son tarifas internas hipotéticas de costo completo, no remuneraciones verificadas. Se justifican por funciones y dedicaciones del diseño y deben reemplazarse por cotizaciones antes de escalar. No se otorga al VAN una certeza superior a sus entradas.',
109:'GPU dedicada: 730 h/mes ×1,20 USD/h =876 USD/mes. La tarifa es una hipótesis sin cotización de proveedor o región; no representa solo GPU activa por 19,3 horas. El monto CPU/RAM, almacenamiento y operación se reserva en infraestructura; al contratar se deberá desglosar para evitar omisiones. Una modalidad bajo demanda tendría otros tiempos de arranque y costos y requiere escenario separado.',
110:'Datos y anotación: 1.500 USD iniciales; capacitación: 1.000 USD; licencias y herramientas: 50 USD/mes. Son partidas explícitas de alcance, sin facturas. El CAPEX total incluye desarrollo más ambas partidas. No se añade entrenamiento facturado a la API ni se atribuye ajuste fino al Qwen usado.',
111:'Capacidad humana: 15,6 % de abstención sobre 50.000 consultas produciría 7.800 derivaciones al mes. Con la hipótesis de tres minutos/caso, 0,20 FTE y 160 h/FTE-mes, el revisor incremental solo atiende 640 casos/mes. Existe una brecha de 7.160. La dotación existente podría absorberla, pero no está comprobado: se exige dimensionar y medir el costo incremental antes de autorizar lanzamiento. El escenario base no es aún un presupuesto operativo aprobado.',
112:'El VAN descuenta flujos mensuales al equivalente de 10 % anual, con inversión inicial y beneficio neto al final de cada mes, sin impuestos ni valor residual. La recuperación es simple, no descontada. El ahorro de 10.000 USD no se suma a ingresos de suscripción: son modelos alternativos. Una caída del beneficio puede invalidar la recomendación incluso si los tokens siguen siendo baratos.',
113:'El Excel separa valores medidos, precios consultados y supuestos. Todas las hojas finales se vinculan mediante fórmulas; los gráficos del informe se construyen a partir de sus valores recalculados. Las versiones anteriores se conservan como históricos y no son anexos vigentes. El único anexo de presupuesto para esta entrega es entrega/Anexo_B_PathInnovate.xlsx.',
116:'La descripción libre puede contener datos personales aunque el producto no los solicite. Por eso se proponen minimización, controles de acceso, retención limitada y aviso de tratamiento. Al 12/11/2026, la Ley 19.628 es la referencia vigente; la Ley 21.719 tiene entrada en vigor diferida al 01/12/2026 según BCN [R3–R4]. El piloto debe preparar esa transición. La clasificación jurídica de operaciones concretas requiere revisión legal antes de producción.',
117:'El Reglamento europeo 2024/1689 se utiliza como referencia de gobernanza y transparencia, en particular su artículo 50 [R5], sin asumir que se aplica automáticamente a toda pyme chilena. Legal deberá analizar ámbito territorial, uso previsto y obligaciones. Las condiciones contractuales de retención y tratamiento del proveedor también deben revisarse. Esta revisión normativa documental no equivale a un dictamen legal.',
120:'Incidente histórico: el feedback recibido informa que la exposición de claves de desarrollo ya fue resuelta. Se actualiza como incidente cerrado según ese antecedente, sin afirmar una verificación independiente de revocación. Permanecen controles preventivos: exclusión de secretos, mínimo privilegio y revisión de paquetes compartidos.',
121:'Las probabilidades e impactos son estimaciones del grupo para priorizar el piloto. Seguridad revisa controles mensualmente y después de incidentes; Calidad revisa métricas por semana. Ninguna de estas frecuencias implica que ya se haya realizado una auditoría en producción.',
124:'Se consideran como escenarios estratégicos los modelos con herramientas, la multimodalidad y cambios de precio. La documentación del modelo muestra herramientas y entradas de imagen [R1]; Hugging Face publica el modelo abierto evaluado [R6]. Son capacidades disponibles, no una estimación cuantificada de mercado ni una garantía de caída sostenida del precio.',
125:'La estrategia evita pronósticos sin evidencia: se modela una baja de diez veces y un aumento de tres veces en tokens, conservando el resto de supuestos. Las fuentes oficiales y fechas se reúnen en Referencias. Estos escenarios permiten decidir con incertidumbre sin presentar como hecho una tendencia de precios no investigada longitudinalmente.',
128:'Suscripción como alternativa al ahorro interno: hipótesis de 1.000 clientes de pago a 5 USD/mes =5.000 USD/mes de ingresos. Con OPEX API de 2.655,58 USD, el margen operativo previo a CAPEX e impuestos es 2.344,42 USD/mes (46,9 %). No hay disposición de pago ni adquisición de clientes validadas. No se suman estos ingresos al beneficio de 10.000 USD usado en el VAN.',
130:'Se elige ahorro interno como caso base de inversión; la suscripción se mantiene como escenario comercial separado en la hoja Escenarios. Se requiere comprobar conversión, soporte y costo de adquisición antes de recomendar ese negocio.',
134:'La propuesta de diferenciación es comparar alternativas con reglas explícitas y costos locales. No se demuestra una superioridad frente a big tech o startups: para hacerlo se necesita benchmark con productos competidores y clientes reales. Un cambio de proveedor requiere reevaluar calidad, contrato y latencia, además de cambiar la URL de API.',
137:'Si los tokens bajan diez veces, el TCO API a 36 meses baja unos 181 USD (0,18 %). La sostenibilidad depende principalmente de beneficio y personal. Si suben tres veces, el Excel recalcula el impacto; el piloto mantendrá cuota de gasto y alertas.',
138:'Si el proveedor principal cambia condiciones, se evaluará otro modelo con el mismo conjunto reservado y revisión legal. Qwen local es una alternativa experimental: 68,8 % interno y p95 12,387 s en la variante verificada; no se asegura equivalencia ni sustitución automática sin degradación.',
143:'Lectura de FINAL3: API RAG y API verificada coinciden en 78/96 respuestas correctas y ninguna cifra sin respaldo observada por el evaluador. El verificador mejora la presencia/validez sintáctica de citas; no se prueba que elimine alucinaciones semánticas. Internamente hay 0/87 sobredimensionadas; externamente 2/27 (7,4 %), que supera ≤5 %. Las repeticiones no equivalen a 96 preguntas independientes.',
145:'El juez automático compara etiquetas y conjuntos de componentes con referencias del grupo. La métrica alucinacion se activa por números ausentes del contexto/pregunta; no es un juez semántico. El conjunto interno incluye 32 preguntas, de las cuales 29 tienen referencia respondible y 3 requieren abstención; el externo incluye 31, 27 respondibles y 4 de abstención. Las métricas de sobredimensión usan esos denominadores respondibles, incluso cuando el sistema se abstiene.',
147:'Las reglas y las etiquetas fueron definidas por el grupo. El conjunto externo fue redactado con ayuda de IA y no consta validación independiente. Se llama externo por ser nuevo respecto al conjunto interno, no por representar una auditoría de expertos ni una muestra probabilística de pymes.',
150:'La comparación entre FINAL2 y FINAL3 es histórica, no un experimento causal: no consta un registro completo de todas las condiciones entre corridas. Para futuras ejecuciones se conservarán hash de corpus/preguntas, commit, versión de dependencias, modelo exacto, parámetros de generación y las filas de todas las repeticiones.',
157:'11.6 Condiciones de validación antes de escalar',
158:'Dos revisores ajenos al grupo etiquetarán independientemente las preguntas, sin ver predicciones ni etiquetas iniciales. Se registrarán identidad, fecha, desacuerdos y adjudicación, sin eliminar silenciosamente casos difíciles. Se informará acuerdo y cambios respecto a la referencia inicial. Esta actividad no ha sido ejecutada y no se presenta como resultado.',
159:'La evaluación externa actual tiene una repetición, sin modelos locales. Una futura corrida externa con tres repeticiones debe guardarse en un directorio nuevo, sin sobrescribir la histórica: python run_eval_asesor.py --repeats 3 --preguntas eval_asesor/preguntas_externas.json --salida eval_asesor/externas_validacion. Requiere acceso a modelos y recursos de ejecución.',
160:'Antes de usar ese conjunto como prueba final se debe congelar corpus, reglas y parámetros. Como las preguntas externas ya fueron inspeccionadas para mejorar el proyecto, conviene reservar un nuevo conjunto independiente para aceptación. La ejecución de FINAL3 en preguntas internas no sustituye esta validación.',
161:'Las figuras comparan conjuntos por separado y mantienen denominadores y fechas. No se combinan las corridas en una única tasa ni se atribuyen métricas de un modelo a toda la aplicación. Los intervalos y el juicio humano se incorporarán en el piloto; las proporciones pequeñas de este benchmark no son garantías de producción.',
166:'Usar el presupuesto único corregido, aprobar las cotizaciones y resolver la brecha de capacidad humana. No se aprueba lanzamiento a 50.000 consultas con el dimensionamiento humano actual.',
167:'Sustituir tarifas internas de planificación por una cotización de costo completo o una decisión presupuestaria firmada; medir costo por caso y tiempo realmente liberado.',
169:'Mantener controles preventivos de secretos; el incidente histórico figura cerrado según el feedback. No se mantiene regeneración como condición activa ya resuelta.',
172:'Si fuéramos el comité, aprobaríamos solo un piloto supervisado y acotado. La recomendación es viable con condiciones para experimentar, no apto para escalar hoy: sobredimensión externa 7,4 %, abstención interna 15,6 %, p95 interno 3,591 s y capacidad humana insuficientemente dimensionada. No aprobaríamos el SLM dedicado por costo y calidad observados. La inversión en lanzamiento queda condicionada al cumplimiento conjunto de las métricas y a beneficio neto validado.',
174:'La columna de páginas se obtiene del PDF renderizado de esta versión. Se justifica expresamente el alcance limitado de planificación, lógica formal y dinámica multiagente; no se marca un tópico como demostrado solo por aparecer en el código.',
176:'Se entrega por separado entrega/Anexo_B_PathInnovate.xlsx. Usa tokens de FINAL3, fórmulas de CAPEX/OPEX, TCO 12/36, VAN, sensibilidad y escenarios. Las versiones Anexo_B_FINAL y v2 son históricas, no anexos vigentes.',
177:'Las celdas distinguen mediciones, precios oficiales y supuestos. Los costos de GPU, roles y automatización no cuentan con validación comercial externa y permanecen como condiciones de inversión, no campos vacíos ni resultados medidos.',
179:'Esta actualización utilizó ChatGPT/Codex para revisión de código, cálculo reproducible, edición del informe y gráficos. Se verificaron resultados contra JSON, fórmulas contra cálculos independientes y código con pruebas automáticas. Las preguntas externas fueron redactadas con ayuda de IA, sin revisión independiente documentada. Cada integrante debe ratificar personalmente su propia declaración antes de entregar; no se atribuyen usos individuales sin evidencia.',
181:'El repositorio no contiene nombres y aportes reales confirmados para este trabajo. Por integridad académica no se deducen de otro proyecto. La siguiente tabla registra la ausencia de ratificación; el anexo D no puede considerarse cerrado hasta que el grupo aporte esa información.',
182:'Referencias y fuentes de consulta',
183:'[R1] OpenAI. GPT-4o mini: modelo, contexto y precios. https://developers.openai.com/api/docs/models/gpt-4o-mini. Consulta: 12/11/2026.',
184:'[R2] Google Cloud. Cloud Run pricing y documentación de GPU. https://cloud.google.com/run/pricing y https://docs.cloud.google.com/run/docs/configuring/services/gpu. Consulta: 12/11/2026. Las tarifas de GPU del Excel son hipótesis; no se atribuyen a estos precios sin región/configuración.',
185:'[R3] Biblioteca del Congreso Nacional de Chile. Ley 19.628. https://www.bcn.cl/leychile/Navegar?dt=open&idLey=19628. Consulta: 12/11/2026.',
186:'[R4] Biblioteca del Congreso Nacional de Chile. Ley 21.719. https://www.bcn.cl/leychile/navegar?i=1209272. Consulta: 12/11/2026. Vigencia diferida: 01/12/2026.',
187:'[R5] Unión Europea. Reglamento (UE) 2024/1689, artículo 50. https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng. Consulta: 12/11/2026.',
188:'[R6] Qwen. Qwen2.5-1.5B-Instruct, ficha y licencia del modelo. https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct. Consulta: 12/11/2026.',
189:'[R7] Evidencias propias: eval_asesor/resultados_asesor_FINAL3.json (12/11/2026), eval_asesor/externas/resultados_asesor.json (10/11/2026), docs/evidencia_feedback.json y docs/portafolio_feedback.json. Fuente administrativa: Feedback_PathInnovate_TAAI2_para_Luis.md; prórroga al 15/11/2026 a las 23:59 de Chile.'
}
changes[144] = "El resultado actual no demuestra eliminación general de alucinaciones: API RAG y API verificada reportan cero cifras sin respaldo y la misma exactitud interna. La externa conserva 7,4 % de sobredimensión y las limitaciones de validación indicadas. El motor de reglas obtuvo 35,5 % externo en su corrida histórica; no se infiere equivalencia con FINAL3."
changes[145] = "11.3 Cómo se juzga"
changes[147] = "11.4 Limitaciones declaradas"
changes[3] = "La solución. Un asesor que recibe una idea o negocio y recomienda una tecnología adecuada mediante reglas y generación con contexto. El prototipo compara un LLM con recuperación de reglas, controles sintácticos y revisión humana. Las decisiones de inversión e implementación corresponden a la persona."
changes[52] = "El benchmark histórico conserva pregunta y respuesta de la repetición 0, verificaciones y métricas agregadas. No conserva el detalle completo de las tres repeticiones ni los contextos recuperados de cada llamada. El código actualizado añade filas completas, identificadores de contexto, hash de corpus/preguntas y commit para futuras ejecuciones. Esta mejora de registro no crea retroactivamente evidencia que falta en FINAL3."
changes[138] += " La ficha oficial consultada marca gpt-4o-mini como deprecated [R1]. Antes del piloto debe verificarse disponibilidad y un reemplazo soportado, con reevaluación de precios y calidad; este informe conserva el modelo realmente medido y no atribuye sus resultados a un sucesor."
for i,t in changes.items():setp(i,t)
# Tables that must no longer state historical values as current.
table_rows(ts[4],[['Formato válido (rep. 0)','32/32 interna; 31/31 externa'],['Citas sintácticas, condicionado a formato','32/32; 31/31'],['Cifras compatibles, condicionado a anteriores','32/32; 31/31'],['Etiqueta correcta, condicionado a anteriores','26/32; 25/31']])
for c,v in zip(ts[4].rows[0].cells,['Control medido','Resultado API verificada']):c.text=v
# Financial table from recalculated workbook.
table_rows(ts[7],[[name,num(w['TCO'].cell(11,c).value),num(w['TCO'].cell(12,c).value),num(w['TCO'].cell(13,c).value),num(w['TCO'].cell(17,c).value),'mes '+str(int(w['TCO'].cell(18,c).value))] for name,c in [('API + RAG + verificador',2),('Mixto SLM/API (diseño)',3),('SLM dedicado',4)]])
table_rows(ts[8],[[w['Sensibilidad'].cell(r,1).value,w['Sensibilidad'].cell(r,2).value,num(w['Sensibilidad'].cell(r,5).value)] for r in [2,3,4,18,19,22]])
table_rows(ts[9],[['Consultas/mes','50.000','Supuesto: 10.000 clientes ×5'],['Tokens entrada/salida','522,7 / 55,3','FINAL3, API verificada'],['Precio API por millón','0,15 / 0,60 USD','OpenAI [R1], 12/11/2026'],['GPU disponible','730 h ×1,20 USD','Reserva dedicada; tarifa supuesta'],['Personal API/mixto/SLM','2.550 / 4.000 / 5.575 USD/mes','Rol × dedicación; hipótesis interna'],['Datos/capacitación','1.500 / 1.000 USD','Supuesto inicial por alcance'],['Licencias','50 USD/mes','Supuesto'],['Costo manual/automatización','0,40 USD / 50 %','Hipótesis de beneficio, no validada'],['Descuento','10 % anual','Hurdle rate supuesto del comité']])
for row in ts[10].rows[1:]:
 if row.cells[0].text.startswith('Técnica'):row.cells[2].text='81,2 % interno; 80,6 % externo; sobredimensión externa 7,4 % y p95 3,591 s: metas incumplidas.'
 if row.cells[0].text.startswith('Económica'):row.cells[1].text='Condicionada';row.cells[2].text='TCO36 API 103.101 USD; VAN hipotético positivo, sujeto a beneficio y capacidad humana.'
 if row.cells[0].text.startswith('Operacional'):row.cells[2].text='7.800 derivaciones/mes frente a 640 casos/mes del revisor incremental supuesto; dimensionamiento requerido.'
for row in ts[11].rows[1:]:
 for c in row.cells:c.text=c.text.replace('regenerar las claves expuestas','incidente histórico cerrado según feedback; controles preventivos').replace('6,5 USD','5,58 USD')
for t in d.tables:
 for row in t.rows:
  for cell in row.cells:
   cell.text=cell.text.replace("pruebas (56)","pruebas automáticas").replace("Pruebas automáticas (56)","Pruebas automáticas").replace("56),", "60),")
# Current evaluation tables.
labels={'llm_solo':'LLM solo','rag_openai':'RAG OpenAI','rag_local':'RAG Qwen','hibrido':'API verificada','hibrido_local':'Qwen verificado','motor_reglas':'Motor reglas'}
pct=lambda x:f'{100*x:.1f} %'.replace('.',',')
keys=['correctas','sobredimensionadas','subdimensionadas','alucinacion','abstenciones']
table_rows(ts[13],[[labels[k]]+[pct(v['metricas'][z]) for z in keys]+[str(v['metricas']['latencia_p50_s'])+' s'] for k,v in internal['configs'].items()])
table_rows(ts[14],[[labels[k]]+[pct(v['metricas'][z]) for z in keys] for k,v in external['configs'].items()])
for t in [ts[13],ts[14]]:t.rows[0].cells[4].text='Cifras sin respaldo'
table_rows(ts[12],[['Recuperación','Recall top-5','1,0 interno; no medido externo','≥0,9'],['Generación','Correctas','81,2 % interno; 80,6 % externo','≥80 %'],['Generación','Sobredimensión','0 % interno; 7,4 % externo','≤5 %; externo NO cumple'],['Control automático','Cifras sin respaldo','Ninguna observada en API verificada','≤2 % + revisión semántica humana'],['Derivación','Abstención','15,6 % interno; 12,9 % externo','≤15 %; interno NO cumple'],['Sistema','Latencia p95','3,591 s interna','≤3 s; NO cumple'],['Sistema','Costo API por consulta','0,000111585 USD','≤0,0003 USD']])
table_rows(ts[15],[['1 Piloto supervisado','4–6 semanas; 200 consultas; validación independiente y revisión humana',f'CAPEX 7.500 + hasta 3 meses OPEX: {num(7500+3*w["TCO"]["B7"].value)} USD','Aprobar partida por etapas, sin compromiso de escala'],['2 Lanzamiento','Solo después de validar calidad, beneficio y dotación','OPEX base 2.655,58 USD/mes; ajustar capacidad humana','Todos los umbrales y capacidad financiada'],['3 Modelo dedicado','Nueva evaluación de demanda, privacidad y calidad','CAPEX hipotético 17.500 USD más OPEX','Calidad comparable y capacidad medidas']])
# Traceability content; pages filled after render.
for row in ts[16].rows[1:]:
 text=' '.join(c.text for c in row.cells)
 last=row.cells[-1]
 last.text=last.text.replace('Pendiente: confirmar el tipo de recuperación','Recuperación léxica por términos; sin embeddings').replace('Producto de precisiones por paso; falta medirlas','Tasas condicionales y conjunta medidas en rep. 0').replace('Verificador: 0 % de alucinaciones','Control sintáctico; sin garantía semántica').replace('Pendiente: explicar que las reglas son proposicionales y que no se usa lógica de primer orden','Predicados proposicionales; sin lógica de primer orden').replace('Flujo de seis acciones resuelto por STRIPS','Workflow fijo; STRIPS solo demostración separada').replace('Replanificación sí; HTN no aplica, el flujo es lineal','Reparación de fallos; HTN no implementado').replace('Pendiente: la comparación no se midió','No medido; alcance justificado en sección 5').replace('Recocido simulado contra óptimo exacto','Portafolio exacto vs voraz; SA solo en reparto de carga').replace('Diseño propuesto; falta un despliegue de prueba','Diseño propuesto; prototipo nube opcional').replace('613 tokens de entrada','522,7 tokens de entrada; FINAL3').replace('0,00013 USD','0,000111585 USD')
# Do not invent authorship.
table_rows(ts[18],[['Identidad del equipo','No ratificada para esta entrega','Confirmación personal requerida'],['Distribución de secciones','No ratificada','El grupo debe declarar aportes reales'],['Defensa del informe','Responsabilidad de todos los firmantes','La generación asistida no sustituye revisión individual']])
# Add figures in their substantive sections.
image_after(22,'fig1_escalera.png','Figura 1. Escalera conceptual ya generada para el proyecto. No implica un orden universal de costos ni sustituye restricciones de privacidad. Fuente: elaboración del proyecto.')
image_after(49,'fig5_arquitectura.png','Figura 2. Arquitectura experimental de generación y verificación. La etiqueta agente corresponde al diseño; el flujo implementado es un workflow controlado. El motor determinista de la interfaz se evalúa por separado.')
image_after(103,'fig2_tco.png','Figura 3. TCO de alternativas a 12 y 36 meses. Fuente: Excel vigente recalculado con FINAL3; las tres alternativas comparten un beneficio hipotético que no demuestra calidad equivalente.')
image_after(105,'fig3_sensibilidad.png','Figura 4. Sensibilidad del VAN de API a 36 meses. El beneficio, no el precio de tokens, determina las principales variaciones. Fuente: hoja Sensibilidad, ±30 %.')
image_after(143,'fig4_evaluacion.png','Figura 5. Evaluación interna FINAL3 y externa histórica. Las proporciones de sobredimensión usan 87 y 27 casos respondibles; no se mezclan conjuntos ni se garantiza ausencia de alucinaciones semánticas.')
# Important added analysis, rather than only removing pending markers.
after(153,'El piloto no automatizará contrataciones ni decisiones irreversibles. Cada caso se etiqueta antes de mostrar la respuesta al revisor, registra tiempo manual y asistido y documenta motivo de derivación. Se conservarán errores y abstenciones para evitar sesgo de selección. El beneficio se estimará por diferencia de tiempo neto con revisión incluida; se informarán casos no resueltos. Los resultados actuales no habilitan lanzamiento hasta cumplir todos los umbrales.')
after(156,'Una métrica entre el umbral de éxito y el de parada impide escalar aunque permita continuar el piloto. Así, 7,4 % de sobredimensión supera 5 % y bloquea lanzamiento, aunque no activa por sí solo el corte de 10 %. El incumplimiento de p95 o la insuficiencia de capacidad también bloquean el hito. Esta distinción evita interpretar la ausencia de parada como éxito.')
after(145,'La regla correcta se recupera con coincidencia léxica de la pregunta contra las 21 reglas. Las preguntas internas se diseñaron sobre ese corpus; no consta muestreo aleatorio ni un registro de revisión por pares. El conjunto externo contiene nuevas formulaciones y casos compuestos. No se conoce una población de referencia que permita extrapolar estas proporciones a todas las pymes. El código de score y el orden ordinal deben auditarse con los revisores antes de aceptar esa referencia como verdad de negocio.')
after(70,'Una comprobación especialmente importante: FINAL3 reporta inventa_fuera_de_corpus=1,0 para Qwen verificado pese a cifras sin respaldo=0. Son métricas distintas: puede contestar indebidamente una pregunta fuera del corpus sin inventar un número. El informe evita llamar alucinación semántica cero a ese resultado. La validación humana debe revisar apoyo de cada afirmación, suficiencia del contexto y adecuación de la recomendación.')
after(108,'Las dedicaciones cubren mantenimiento de prompts/corpus, pruebas y operación; no incluyen el tiempo original de atención manual ya incluido en el beneficio. La tarifa interna se descompone como costo completo presupuestario por rol. Hasta contar con una cotización o aprobación financiera, una sensibilidad no convierte esa tarifa en dato de mercado. La partida de anotación inicial es separada de la revisión recurrente y debe registrarse para evitar solapamiento.')
after(91,'El portafolio con restricciones se mide con seis candidatas, horas ilustrativas y una dependencia del RAG respecto del bot de reglas. El informe de ejecución guarda selección exacta, línea base voraz y tiempo de cómputo. Se comprueba factibilidad y que el exacto no empeore el objetivo del voraz. No hay ruteo temporal, precedencias de calendario ni asignación nominal de personas; estos problemas requieren un planificador adicional si el producto los incorpora.')
# Use 11pt body and clean readable table styling.
for style in d.styles:
 if style.type==1:
  style.font.name='Arial';style.font.color.rgb=RGBColor(0,0,0)
for p in d.paragraphs:
 for run in p.runs:
  if not run._r.xpath('.//w:drawing'):run.font.name='Arial';run.font.size=Pt(11)
 p.paragraph_format.space_after=Pt(7);p.paragraph_format.line_spacing=1.12
 if re.match(r'^\d+\. [A-ZÁÉÍÓÚ]',p.text) or p.text.startswith('Anexo '):
  p.style=d.styles['Heading 1'];p.paragraph_format.page_break_before=(p.text.startswith(('0. ', '1. ', 'Anexo A.')));p.paragraph_format.keep_with_next=True
  for r in p.runs:r.font.size=Pt(15);r.bold=True
 elif re.match(r'^\d+\.\d+ ',p.text):
  p.paragraph_format.keep_with_next=True
  for r in p.runs:r.font.size=Pt(12);r.bold=True
for t in d.tables:
 for ri,row in enumerate(t.rows):
  row._tr.get_or_add_trPr().append(OxmlElement('w:cantSplit'))
  for cell in row.cells:
   for p in cell.paragraphs:
    p.paragraph_format.space_after=Pt(4)
    for run in p.runs:run.font.name='Arial';run.font.size=Pt(11);run.bold=(ri==0)
   pr=cell._tc.get_or_add_tcPr();b=OxmlElement('w:tcBorders')
   for side in ['top','left','bottom','right']:
    e=OxmlElement('w:'+side);e.set(qn('w:val'),'single');e.set(qn('w:sz'),'4');e.set(qn('w:color'),'D9D9D9');b.append(e)
   pr.append(b)
 if t.rows:
  prop=t.rows[0]._tr.get_or_add_trPr();prop.append(OxmlElement('w:tblHeader'))
ps[0].style=d.styles['Title']
for r in ps[0].runs:r.font.size=Pt(22);r.bold=True
# Short, readable metric headings within narrow comparison columns.
for t in [ts[13],ts[14]]:
 t.rows[0].cells[1].text="Acierto %"
 t.rows[0].cells[5].text="Abst. %"
# Footer field page numbers.
for section in d.sections:
 p=section.footer.paragraphs[0];p.alignment=2;fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');p._p.append(fld)
# Canonical report metadata.
d.core_properties.title='Evaluación de presupuesto y factibilidad de PathInnovate';d.core_properties.subject='Correcciones del feedback TAAI2 y evidencia FINAL3';d.core_properties.author='Equipo PathInnovate'
# Optional page mapping from most recent render supplied by verifier.
mapfile=ROOT/'docs/paginas_feedback.json'
if mapfile.exists():
 mapping=json.loads(mapfile.read_text())
 for row in ts[16].rows[1:]:
  sec=row.cells[2].text;parts=re.findall(r'\d+(?:\.\d+)?',sec);pages=[]
  for part in parts:
   page=mapping.get(part) or mapping.get(part.split('.')[0])
   if page and page not in pages:pages.append(page)
  row.cells[3].text=', '.join(str(x) for x in pages) or 'Ver sección indicada'
d.save(ROOT/'entrega/Informe_PathInnovate.docx')
# Also export text for review and reproducibility.
print('Informe actualizado:',len(d.paragraphs),'párrafos;',len(d.inline_shapes),'figuras')
