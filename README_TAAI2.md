# Magister Copilot - Módulo TAAI2 (Evaluación Presupuesto y Factibilidad)

Este módulo amplía el repositorio base `magister-copilot` / `PathInnovate` para cumplir explícitamente con los criterios de evaluación de la **Tarea Grupal (45%)** de **Tópicos Avanzados en Inteligencia Artificial 2**.

---

## 🚀 Comandos Rápidos

### 1. Planificar un Proyecto de Innovación (Sesiones 1 a 5)
Ejecuta el planificador neuro-simbólico para generar una hoja de ruta con validaciones y grounding:
```bash
python -m copilot.engine_taai2 plan "Desarrollar un copiloto de atención ciudadana con ruteo automático y reglas presupuestarias"
```

### 2. Calcular Presupuesto a 12 y 36 Meses (Sesión 6 & Anexo B)
Estima el **CAPEX** y **OPEX** comparando estrategias de API vs. SLM hospedado (Cloud Run / GPUs):
```bash
# Estrategia basada en API comercial
python -m copilot.engine_taai2 budget --queries 50000 --strategy api

# Estrategia basada en SLM propio en infraestructura dedicada
python -m copilot.engine_taai2 budget --queries 50000 --strategy slm_self_hosted
```

### 3. Generar la Matriz de Trazabilidad (Anexo A)
Genera automáticamente la tabla requerida en el **Anexo A** del informe PDF:
```bash
python -m copilot.engine_taai2 traceability
```

---

## 📋 Estructura Integrada del Syllabus

| Sesión Syllabus | Módulo Interno | Aplicación en la Solución |
|---|---|---|
| **S1: Modelos Fundacionales** | `BudgetCalculator` & `InnovationPlanner` | Elección entre LLM y SLM destilado, cálculo de consumo de tokens por consulta. |
| **S2: IA Autónoma & Agentes** | `SymbolicVerifier` | Definición de orquestador y patrón **Humano en el Circuito**. |
| **S3: Razonamiento Simbólico** | `SymbolicVerifier` | Reglas duras para prevenir alucinaciones y asegurar privacidad. |
| **S4: Planificación** | `InnovationPlanner` | Estructuración secuencial de etapas con metas y dependencias. |
| **S5: Optimización** | `InnovationPlanner` | Asignación eficiente de recursos y límites de latencia. |
| **S6: Economía de la IA** | `BudgetCalculator` | Proyección financiera TCO (CAPEX/OPEX), sensibilidad a 12 y 36 meses. |

---

## 📝 Pasos Recomendados para la Entrega Final
1. **Informe PDF (20 a 35 páginas):** Utilizar las salidas en JSON del comando `plan` y `budget` como respaldo directo de las secciones 2 a 8 del informe.
2. **Anexo A:** Copiar la tabla Markdown generada por el comando `traceability`.
3. **Anexo B:** Exportar los resultados de `budget` a la planilla Excel requerida.