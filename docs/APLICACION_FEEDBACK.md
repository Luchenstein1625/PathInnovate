# Aplicación del feedback de PathInnovate

Base: main 59006ea, con la corrida interna FINAL3 del 12/11/2026. Se preserva la externa histórica del 10/11/2026. No se ejecutaron nuevas llamadas a modelos durante esta revisión.

Los entregables vigentes están en `entrega/`. Los archivos raíz de Word/PDF se sincronizan con esos entregables. Anexo_B_v2 y resultados FINAL/FINAL2 son históricos.

| Observación | Corrección y evidencia | Límite que permanece |
|---|---|---|
| Confiabilidad de la cadena | Tasas condicionales y conjuntas desde respuestas archivadas; scripts/evidence_feedback.py y sección 3.4 | Solo repetición 0 archivada en FINAL3; no reconstruye 96 filas |
| Gobernanza | Dueños por rol, revisión por cambio, auditoría mensual y corpus trimestral, sección 3.3 | Responsabilidades propuestas de consultora ficticia |
| STRIPS | Se reconoce workflow fijo; demostración STRIPS separada; sección 5 | No hay experimento de planificación abierta |
| Optimización de pymes | Portafolio exacto y voraz con presupuesto, horas y dependencias, pruebas y JSON de ejecución | Datos ilustrativos; no calendario ni personas nominales |
| Evaluación | Método, denominadores y origen declarados; sin atribuir validación externa a preguntas generadas con IA | Etiquetado independiente aún no realizado |
| Repeticiones externas | La externa histórica permanece 31×1, sin modelos locales | Su repetición requiere recursos y ejecución del grupo |
| Despliegue | Separación prototipo local/diseño Cloud Run, sección 7 | No se afirma despliegue productivo |
| Generalización de 0 % | Ninguna cifra sin respaldo observada según detector numérico; no garantía semántica | La revisión humana semántica falta |
| Sobredimensión | 0/87 interna y 2/27 externa; 7,4 % incumple ≤5 % | Bloquea lanzamiento |
| FINAL3 | Exactitud 78/96, abstención 15,6 %, p95 3,591 s; tablas y gráficos actuales | Abstención y p95 también incumplen metas |
| Tokens | Base única FINAL3: 522,7 entrada, 55,3 salida, 0,000111585 USD/caso | Promedios redondeados; tarifa no garantiza disponibilidad futura |
| Presupuesto | CAPEX/OPEX completos, personal por rol, GPU 730 h, datos, capacitación y licencias | Tarifas internas/GPU no son cotizaciones verificadas |
| Finanzas | Fórmulas VAN, recuperación, TCO y sensibilidad; diferenciación entre cruce OPEX y escala factible | Automatización 50 % y beneficio 10.000 USD/mes son hipótesis |
| Capacidad | 7.800 posibles derivaciones frente a capacidad incremental 640/mes | Dimensionar equipo existente y costo antes de escalar |
| Gráficos | Cinco figuras integradas en Word/PDF; tres regeneradas con FINAL3 y Excel actual | Escalera y arquitectura son esquemas conceptuales con salvedades |
| Anexo A | Páginas contrastadas con PDF renderizado | No sustituye contraste del grupo con syllabus íntegro |
| Anexo C | Uso de IA de esta revisión declarado; usos históricos conservados | Cada integrante ratifica su declaración |
| Anexo D | Ausencia de ratificación explícita; no se inventan nombres/aportes | Información personal del grupo requerida para cerrar entrega |
| Administración | Fecha 15/11/2026 23:59 Chile; incidente de claves histórico cerrado según feedback | No se afirma auditoría independiente de revocación |

## Validación ejecutada

- 61 pruebas automáticas del repositorio, con casos nuevos de restricciones y entradas inválidas.
- Comparación independiente entre BudgetCalculator y valores recalculados de Excel para TCO y VAN de tres alternativas.
- Edición de entradas de tokens, tasa cero y abstención sobre copia de trabajo del Excel; recálculo dependiente y restauración de entradas.
- Verificación de fórmulas sin errores y revisión de vistas de hojas.
- Render del Word a PDF, figuras insertadas y comprobación de páginas de trazabilidad.

## Reproducción

Desde la raíz del repositorio:

```powershell
python -m unittest discover -s tests -t .
python scripts/evidence_feedback.py
python -m copilot.engine_taai2 portfolio --presupuesto 12000 --horas 70 --json docs/portafolio_candidatas.json
python -m copilot.engine_taai2 budget --queries 50000 --strategy all
```

La edición final de Excel usa `scripts/actualizar_anexo.mjs` con Artifact Tool en el entorno de autoría. `scripts/informe_feedback.py` usa el presupuesto ya recalculado y una copia histórica del Word como plantilla. `scripts/figuras_feedback.py` regenera figuras exactas con matplotlib. Las mediciones históricas no se reescriben.
