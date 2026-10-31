"""Valores por defecto. Lo que está aquí es una PROPUESTA inicial, no el syllabus oficial.

Los tópicos (TOPICS) se derivan de la tabla del enunciado de la tarea TAAI2 y deben
revisarse contra SYLLABUS_TAAI.pdf (paso 5 del README). Las horas de SECTIONS son supuestos.
"""

# Cursos según los prefijos numéricos de las carpetas (no existe la carpeta 08).
COURSES = {
    "01": "Introducción a la IA y Ciencias Cognitivas",
    "02": "Representación de Conocimientos",
    "03": "Técnicas de Búsqueda y Heurísticas",
    "04": "Aprendizaje Automático",
    "05": "Agentes Inteligentes",
    "06": "Computer Vision",
    "07": "Procesamiento de Lenguaje Natural",
    "09": "Tópicos Emergentes en IA",
    "10": "Aprendizaje Profundo",
    "11": "Taller de Diseño e Innovación",
    "12": "Simulación Basada en Agentes",
    "13": "Visión Artificial",
    "14": "Tópicos Avanzados en IA 1",
    "15": "Sistemas Bioinspirados",
    "16": "Tópicos Avanzados en IA 2 (TAAI2)",
    "OTROS": "Otros (calendario, libros, papers, capstone)",
    "CAPSTONE": "Capstone (resumen)",
    "ROOT": "Raíz",
}
TAAI2 = "16"

# Los .md de la raíz traen numeración corrida: 15_Topicos_Avanzados_IA_II.md es la carpeta 16.
# Clave: nombre normalizado sin el prefijo numérico.
ROOT_MD = {
    "introduccion ia": "01",
    "representacion conocimiento": "02",
    "busqueda heuristicas": "03",
    "aprendizaje automatico": "04",
    "agentes inteligentes": "05",
    "computer vision": "06",
    "procesamiento lenguaje natural": "07",
    "topicos emergentes": "09",
    "deep learning": "10",
    "taller diseno": "11",
    "simulacion agentes": "12",
    "topicos avanzados ia i": "14",
    "topicos avanzados ia ii": "16",
    "capstone mapping": "CAPSTONE",
}

KIND_WEIGHT = {
    "resumen": 1.5,
    "syllabus": 1.3,
    "evaluacion": 1.2,
    "transcript": 1.0,
    "slides": 1.0,
    "material": 0.9,
    "notebook": 0.8,
    "otro": 0.7,
    "libro": 0.6,
    "chat": 0.5,
}

# Cursos previos que alimentan cada sesión de TAAI2 (inferido de los nombres de archivo; validar).
SUPPORT = {
    "S1": ["07", "14", "09", "01"],
    "S2": ["05", "12", "09"],
    "S3": ["02"],
    "S4": ["03", "05"],
    "S5": ["03", "15", "04"],
    "S6": ["11", "09", "01"],
    "T": ["04", "10"],
}

# (sesión, id, tópico, palabras clave separadas por ';', sección(es) del informe separadas por ';')
TOPICS = [
    ("S1", "S1.1", "Tipos de modelo: LLM causal, MLM, multimodal, SLM, de dominio",
     "LLM;SLM;small language model;modelo pequeno;modelo fundacional;foundation model;multimodal;VLM;masked language model;modelo de dominio;xLM;encoder;decoder;self attention", "2"),
    ("S1", "S1.2", "Adaptación: ICL, RAG, LoRA/PEFT, destilación",
     "in-context learning;RAG;retrieval augmented;LoRA;PEFT;fine tuning;ajuste fino;destilacion;distillation;modelo destilado;modelo estudiante", "2"),
    ("S1", "S1.3", "Contexto, tokens y costo por consulta",
     "ventana de contexto;context window;tokens;tokenizacion;costo por token;precio por token", "2;8"),
    ("S1", "S1.4", "Representación distribuida vs simbólica",
     "embeddings;representacion distribuida;representacion simbolica;espacio latente", "2"),
    ("S2", "S2.1", "Arquitectura agentic: agentes, hubs, orquestador, memoria, herramientas",
     "agente;multiagente;orquestador;hub;workflow;fiscalizador;estado compartido;tool use;herramientas;memoria;MCP", "3"),
    ("S2", "S2.2", "Niveles de autonomía y humano en el circuito",
     "autonomia;grado de autonomia;nivel de criticidad;human in the loop;humano en el loop;humano en el circuito;supervision;accion irreversible", "3"),
    ("S2", "S2.3", "Confiabilidad de la cadena (precisión por paso a precisión del flujo)",
     "confiabilidad;probabilidad de exito;punta a punta;error compuesto;precision por paso;cadena de agentes;fiabilidad", "3"),
    ("S2", "S2.4", "Sistemas complejos y dinámica entre agentes",
     "sistemas complejos;emergencia;simulacion basada en agentes;auto organizacion", "3"),
    ("S2", "S2.5", "Gobernanza, trazabilidad y auditoría",
     "gobernanza;trazabilidad;auditoria;accountable;EU AI Act;AI Act;regulacion;ciberseguridad", "3;9"),
    ("S3", "S3.1", "Reglas duras, ontologías y grafos de conocimiento",
     "ontologia;grafo de conocimiento;knowledge graph;reglas;reglas de negocio;logica discreta;restricciones", "4"),
    ("S3", "S3.2", "Neurosimbólico, grounding y verificación",
     "neurosimbolico;neuro simbolico;neuro symbolic;grounding;verificacion;verificador;alucinacion", "4"),
    ("S3", "S3.3", "Razonamiento lógico (proposicional y de primer orden)",
     "logica proposicional;logica de primer orden;inferencia;prolog;razonamiento simbolico", "4"),
    ("S4", "S4.1", "Planificación clásica: STRIPS / PDDL",
     "STRIPS;PDDL;planificacion;planificador clasico;estado inicial;precondiciones;efectos", "5"),
    ("S4", "S4.2", "HTN y replanificación",
     "HTN;tareas jerarquicas;replanificacion;hierarchical task network", "5"),
    ("S4", "S4.3", "LLM como planificador vs planificador simbólico",
     "planificacion con LLM;planificador clasico;chain of thought;ReAct;plan and solve", "5"),
    ("S5", "S5.1", "Formulación de optimización y problemas NP-duros",
     "optimizacion;funcion objetivo;restricciones;NP duro;NP hard;espacio de busqueda", "6"),
    ("S5", "S5.2", "Metaheurísticas: SA, GA, PSO, búsqueda local",
     "simulated annealing;recocido simulado;algoritmo genetico;genetic algorithm;PSO;enjambre;busqueda local;metaheuristica;hormigas", "6"),
    ("S5", "S5.3", "IA generativa en optimización (FunSearch)",
     "FunSearch;AlphaEvolve;optimizacion con LLM", "6"),
    ("S5", "S5.4", "Despliegue: Cloud Run, Hugging Face Hub, Finbot, CI/CD",
     "Cloud Run;Hugging Face;HF Hub;Finbot;CI/CD;despliegue;docker;dockerfile;locust;github;escalar;desescalar;rollback;observabilidad", "7"),
    ("S6", "S6.1", "Economía de la IA: CAPEX, OPEX, TCO, punto de equilibrio",
     "TCO;CAPEX;OPEX;VAN;punto de equilibrio;costo total;economia de la IA", "8"),
    ("S6", "S6.2", "Estrategia y modelo de negocio",
     "modelo de negocio;AI as a service;plataforma;big tech;startups;captura de valor;estrategia", "10"),
    ("S6", "S6.3", "Mercado, tendencias y precios de modelos",
     "precio de tokens;costo de inferencia;tendencias;scaling laws;modelo abierto;open source", "10"),
    ("S6", "S6.4", "Riesgos: dependencia y concentración de proveedores",
     "dependencia tecnologica;concentracion de proveedores;vendor lock in;riesgo;seguridad", "9"),
    ("S6", "S6.5", "Tokens y activos descentralizados",
     "token;blockchain;descentralizado;cripto;DAO", "10"),
    ("T", "T.1", "Evaluación: métricas, set fijo, juez y piloto",
     "evaluacion;benchmark;LLM as judge;metricas;piloto;conjunto de evaluacion", "11"),
]

# (id, sección, horas estimadas [supuesto], depende_de, día límite 1..14, perfil)
# Día 1 = lun 26-oct-2026, día 14 = dom 8-nov-2026.
SECTIONS = [
    ("ARQ", "Arquitectura base y reparto de componentes", 4, "", 3, "arquitectura"),
    ("XLS", "Excel de supuestos (estructura)", 3, "ARQ", 3, "finanzas"),
    ("S01", "Sec. 1 La solución y el problema", 5, "ARQ", 3, "negocio"),
    ("S02", "Sec. 2 Modelos fundacionales (S1)", 7, "ARQ", 5, "llm"),
    ("S03", "Sec. 3 Autonomía, agentes y gobernanza (S2)", 7, "ARQ", 5, "agentes"),
    ("S04", "Sec. 4 Razonamiento simbólico (S3)", 5, "ARQ", 6, "simbolico"),
    ("S05", "Sec. 5 Planificación (S4)", 5, "ARQ", 6, "planificacion"),
    ("S06", "Sec. 6 Optimización (S5)", 6, "ARQ", 7, "optimizacion"),
    ("S07", "Sec. 7 Despliegue y operación", 6, "ARQ", 7, "cloud"),
    ("S08", "Sec. 8 Presupuesto (S6)", 9, "S02;S07;XLS", 11, "finanzas"),
    ("S09", "Sec. 9 Factibilidad y riesgos", 7, "S03;S08", 11, "riesgo"),
    ("S10", "Sec. 10 Estrategia y modelo de negocio", 5, "S08", 11, "negocio"),
    ("S11", "Sec. 11 Plan de evaluación", 5, "S02;S03;S04;S05;S06", 11, "llm"),
    ("S12", "Sec. 12 Recomendación", 3, "S08;S09;S10;S11", 13, "escritura"),
    ("S00", "Sec. 0 Resumen ejecutivo", 3, "S12", 13, "escritura"),
    ("AA", "Anexo A Tabla de trazabilidad", 4, "S11", 13, "escritura"),
    ("AB", "Anexo B Excel completo con fuentes y fechas", 5, "S08", 12, "finanzas"),
    ("AC", "Anexo C Declaración de uso de IA", 2, "S12", 14, "escritura"),
    ("AD", "Anexo D Aportes por integrante", 1, "S12", 14, "escritura"),
    ("REV", "Lectura cruzada y PDF final", 5, "S00;AA;AB;AC;AD", 14, "escritura"),
]

# (nombre, horas por día hábil, horas por día de fin de semana, fortalezas ';', días sin disponibilidad ';')
TEAM = [
    ("Integrante 1", 3.0, 5.0, "arquitectura;llm", ""),
    ("Integrante 2", 3.0, 5.0, "agentes;simbolico;planificacion", ""),
    ("Integrante 3", 3.0, 5.0, "finanzas;negocio;riesgo", ""),
    ("Integrante 4", 3.0, 5.0, "cloud;optimizacion;escritura", ""),
]

# Sesiones de TAAI2: fecha de la grabación -> sesión. Confirmadas con el enunciado (el 26-oct fue la Sesión 5)
# y con el contenido de cada grabación. Corrígelas si el calendario del curso cambia.
TAAI2_SESSIONS = {
    "2026-09-21": "S1",
    "2026-09-28": "S2",
    "2026-10-05": "S3",
    "2026-10-19": "S4",
    "2026-10-26": "S5",
}
TAAI2_ALL_SESSIONS = ["S1", "S2", "S3", "S4", "S5", "S6"]
