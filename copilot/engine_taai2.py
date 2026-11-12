"""Magister Copilot - modulo TAAI2 (S1-S6). Presupuesto, confiabilidad, riesgos, planificacion, optimizacion, trazabilidad y chequeo de PDF."""
import argparse, csv, json, math, random, re, sys
from collections import deque
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Dict, List, Optional

SYLLABUS_MAP = {
    "S1": {"title": "Modelos fundacionales y adaptacion", "secs": "2"},
    "S2": {"title": "IA autonoma y sistemas complejos", "secs": "3;9"},
    "S3": {"title": "Razonamiento simbolico y logico", "secs": "4"},
    "S4": {"title": "Planificacion avanzada", "secs": "5"},
    "S5": {"title": "Optimizacion y despliegue", "secs": "6;7"},
    "S6": {"title": "Economia de la IA y estrategia", "secs": "8;9;10"},
}

# ---------------- S3: verificador simbolico ----------------
class SymbolicVerifier:
    """Reglas duras sobre una propuesta (dict). Cada regla devuelve True si se cumple."""
    def __init__(self):
        self.rules = {
            "RULE_LATENCY": ("latencia_max_ms <= 5000", lambda p: p.get("latencia_max_ms", 0) <= 5000),
            "RULE_BUDGET": ("presupuesto_usd definido y > 0", lambda p: p.get("presupuesto_usd", 0) > 0),
            "RULE_HITL": ("acciones irreversibles requieren humano", lambda p: not p.get("accion_irreversible") or p.get("humano_en_circuito", False)),
            "RULE_PII": ("datos personales requieren anonimizacion", lambda p: not p.get("usa_datos_personales") or p.get("anonimizado", False)),
        }

    def verify(self, ctx: Dict[str, Any]) -> List[str]:
        bad = []
        for rid, (_, fn) in self.rules.items():
            try:
                ok = fn(ctx)
            except Exception:
                ok = False
            if not ok:
                bad.append(rid)
        return bad

# ---------------- S2: confiabilidad de la cadena ----------------
def chain_reliability(acc: List[float], hitl: Optional[Dict[int, float]] = None) -> Dict[str, Any]:
    """acc: precision por paso. hitl: {indice_paso: fraccion de errores que el humano detecta}."""
    hitl = hitl or {}
    flow = math.prod(acc)
    eff = [a + (1 - a) * hitl.get(i, 0.0) for i, a in enumerate(acc)]
    return {"pasos": len(acc), "precision_flujo": round(flow, 4),
            "precision_flujo_con_humano": round(math.prod(eff), 4)}

# ---------------- S6: presupuesto ----------------
# (valor, unidad, fuente, fecha). Son SUPUESTOS: verificar precios en paginas oficiales antes de citarlos.
FUENTE_PRECIO = "Supuesto del grupo; VERIFICAR en pagina oficial del proveedor"
_CURRENT = json.loads((Path(__file__).resolve().parents[1] / "config/budget_current.json").read_text(encoding="utf-8"))["assumptions"]
@dataclass
class Assumptions:
    monthly_queries: int = _CURRENT["monthly_queries"]
    prompt_tokens: int = _CURRENT["prompt_tokens"]
    completion_tokens: int = _CURRENT["completion_tokens"]
    api_in_per_mtok: float = _CURRENT["api_in_per_mtok"]
    api_out_per_mtok: float = _CURRENT["api_out_per_mtok"]
    gpu_hour: float = _CURRENT["gpu_hour"]
    gpu_hours_month: float = _CURRENT["gpu_hours_month"]
    infra_base_month: float = _CURRENT["infra_base_month"]
    personnel_api: float = _CURRENT["personnel_api"]
    personnel_self: float = _CURRENT["personnel_self"]
    personnel_hybrid: float = _CURRENT["personnel_hybrid"]
    capex_api: float = _CURRENT["capex_api"]
    capex_self: float = _CURRENT["capex_self"]
    capex_hybrid: float = _CURRENT["capex_hybrid"]
    slm_share_hybrid: float = _CURRENT["slm_share_hybrid"]
    manual_cost_per_case: float = _CURRENT["manual_cost_per_case"]
    automation_rate: float = _CURRENT["automation_rate"]
    discount_rate_annual: float = _CURRENT["discount_rate_annual"]

    infra_api_month: float = _CURRENT["infra_api_month"]
    licenses_month: float = _CURRENT["licenses_month"]
    data_capex: float = _CURRENT["data_capex"]
    training_capex: float = _CURRENT["training_capex"]
    def table(self) -> List[tuple]:
        d = "2026-11-12"
        units = {"monthly_queries": "consultas/mes", "prompt_tokens": "tokens", "completion_tokens": "tokens",
                 "api_in_per_mtok": "USD/1M tok", "api_out_per_mtok": "USD/1M tok", "gpu_hour": "USD/h",
                 "gpu_hours_month": "h/mes", "discount_rate_annual": "tasa", "slm_share_hybrid": "fraccion",
                 "automation_rate": "fraccion"}
        return [(k, v, units.get(k, "USD" if "/" not in k else ""),
                 FUENTE_PRECIO if k.startswith(("api_", "gpu")) else "Supuesto del grupo (justificar en informe)", d)
                for k, v in self.__dict__.items()]

STRATEGIES = ("api", "slm_self_hosted", "hybrid")

class BudgetCalculator:
    def __init__(self, monthly_queries: int = 50000, assumptions: Optional[Assumptions] = None):
        self.a = assumptions or Assumptions(monthly_queries=monthly_queries)

    def _monthly(self, s: str) -> Dict[str, float]:
        a, q = self.a, self.a.monthly_queries
        def tok(n):
            return n * (a.prompt_tokens * a.api_in_per_mtok + a.completion_tokens * a.api_out_per_mtok) / 1e6
        gpu = a.gpu_hour * a.gpu_hours_month
        if s == "api":
            return {"tokens": tok(q), "infra": a.infra_api_month, "personal": a.personnel_api, "licencias": a.licenses_month}
        if s == "slm_self_hosted":
            return {"tokens": 0.0, "infra": gpu + a.infra_base_month, "personal": a.personnel_self, "licencias": a.licenses_month}
        if s == "hybrid":
            return {"tokens": tok(q * (1 - a.slm_share_hybrid)), "infra": gpu + a.infra_base_month, "personal": a.personnel_hybrid, "licencias": a.licenses_month}
        raise ValueError(s)

    def _capex(self, s: str) -> float:
        return {"api": self.a.capex_api, "slm_self_hosted": self.a.capex_self, "hybrid": self.a.capex_hybrid}[s] + self.a.data_capex + self.a.training_capex

    def _benefit(self) -> float:
        return self.a.monthly_queries * self.a.automation_rate * self.a.manual_cost_per_case

    def compute_tco(self, months: int = 12, strategy: str = "api") -> Dict[str, Any]:
        m = self._monthly(strategy)
        opex, capex = sum(m.values()) * months, self._capex(strategy)
        return {"horizonte_meses": months, "estrategia": strategy, "capex_usd": round(capex, 2), "opex_usd": round(opex, 2),
                "desglose_opex": {"inferencia_tokens_usd": round(m["tokens"] * months, 2),
                                  "infraestructura_cloud_usd": round(m["infra"] * months, 2),
                                  "personal_operaciones_usd": round(m["personal"] * months, 2), "licencias_usd": round(m["licencias"] * months, 2)},
                "tco_total_usd": round(capex + opex, 2)}

    def npv(self, months: int, strategy: str) -> float:
        r = (1 + self.a.discount_rate_annual) ** (1 / 12) - 1
        net = self._benefit() - sum(self._monthly(strategy).values())
        return round(-self._capex(strategy) + sum(net / (1 + r) ** t for t in range(1, months + 1)), 2)

    def break_even_month(self, strategy: str, max_months: int = 120) -> Optional[int]:
        net = self._benefit() - sum(self._monthly(strategy).values())
        if net <= 0:
            return None
        return math.ceil(self._capex(strategy) / net)

    def evaluate(self, strategy: str) -> Dict[str, Any]:
        return {"estrategia": strategy,
                "evaluacion_12_meses": {**self.compute_tco(12, strategy), "van_usd": self.npv(12, strategy)},
                "evaluacion_36_meses": {**self.compute_tco(36, strategy), "van_usd": self.npv(36, strategy)},
                "punto_equilibrio_mes": self.break_even_month(strategy)}

    def sensitivity(self, strategy: str, delta: float = 0.3, months: int = 36) -> List[Dict[str, Any]]:
        """Oscila +-delta cada variable y mide el cambio del VAN. Devuelve las 3 de mayor efecto."""
        out = []
        for var in ("monthly_queries", "api_in_per_mtok", "api_out_per_mtok", "gpu_hour", "personnel_api",
                    "personnel_self", "personnel_hybrid", "manual_cost_per_case", "automation_rate"):
            res = []
            for f in (1 - delta, 1 + delta):
                c = BudgetCalculator(assumptions=replace(self.a, **{var: getattr(self.a, var) * f}))
                res.append(c.npv(months, strategy))
            out.append({"variable": var, "van_bajo": res[0], "van_alto": res[1], "oscilacion": round(abs(res[1] - res[0]), 2)})
        return sorted(out, key=lambda x: -x["oscilacion"])[:3]

    def export_xlsx(self, path: str) -> str:
        from openpyxl import Workbook
        wb = Workbook(); ws = wb.active; ws.title = "Supuestos"
        ws.append(["Variable", "Valor", "Unidad", "Fuente / supuesto", "Fecha consulta"])
        for row in self.a.table():
            ws.append(list(row))
        t = wb.create_sheet("TCO")
        t.append(["Estrategia", "Meses", "CAPEX", "OPEX", "TCO (=CAPEX+OPEX)", "VAN", "Punto equilibrio (mes)"])
        for s in STRATEGIES:
            for mth in (12, 36):
                c = self.compute_tco(mth, s); r = t.max_row + 1
                t.append([s, mth, c["capex_usd"], c["opex_usd"], f"=C{r}+D{r}", self.npv(mth, s), self.break_even_month(s)])
        sn = wb.create_sheet("Sensibilidad")
        sn.append(["Estrategia", "Variable", "VAN -30%", "VAN +30%", "Oscilacion"])
        for s in STRATEGIES:
            for x in self.sensitivity(s):
                sn.append([s, x["variable"], x["van_bajo"], x["van_alto"], x["oscilacion"]])
        wb.save(path)
        return path

# ---------------- S9: riesgos ----------------
def risk_register() -> List[Dict[str, Any]]:
    """Plantilla: ADAPTAR a la solucion elegida (probabilidad e impacto 1-5)."""
    base = [
        ("Dependencia de un proveedor de API", 4, 4, "Capa de abstraccion + modelo abierto de respaldo", "Arquitecto"),
        ("Alucinaciones en decisiones con efecto", 3, 5, "Verificador simbolico + humano en acciones irreversibles", "Lider IA"),
        ("Costo variable de tokens fuera de presupuesto", 3, 4, "Cuotas, cache, enrutamiento a SLM", "Finanzas"),
        ("Incumplimiento de datos personales / sectorial", 2, 5, "Anonimizacion, DPIA, bitacora de auditoria", "Legal"),
        ("Baja adopcion por usuarios", 3, 3, "Piloto con champions y capacitacion", "Negocio"),
        ("Fuga de datos / prompt injection", 2, 5, "Filtros, minimo privilegio, pentest", "Seguridad"),
        ("Deriva del modelo y degradacion de calidad", 3, 3, "Set de evaluacion fijo y monitoreo", "MLOps"),
    ]
    rows = [{"riesgo": r, "prob": p, "impacto": i, "score": p * i, "mitigacion": m, "dueno": d} for r, p, i, m, d in base]
    return sorted(rows, key=lambda x: -x["score"])

# ---------------- S4: planificacion STRIPS ----------------
ACTIONS = {
    "clasificar": ({"caso"}, {"clasificado"}),
    "recuperar_reglas": ({"clasificado"}, {"reglas"}),
    "redactar": ({"reglas"}, {"borrador"}),
    "verificar": ({"borrador"}, {"verificado"}),
    "aprobar_humano": ({"verificado"}, {"aprobado"}),
    "ejecutar": ({"verificado", "aprobado"}, {"ejecutado"}),
}

def strips_plan(init=frozenset({"caso"}), goal=frozenset({"ejecutado"}), actions=ACTIONS) -> Optional[List[str]]:
    q, seen = deque([(frozenset(init), [])]), {frozenset(init)}
    while q:
        s, path = q.popleft()
        if goal <= s:
            return path
        for name, (pre, eff) in actions.items():
            if pre <= s:
                n = s | eff
                if n not in seen:
                    seen.add(n); q.append((n, path + [name]))
    return None

class InnovationPlanner:
    def __init__(self):
        self.verifier = SymbolicVerifier()

    def generate_plan(self, goal: str) -> Dict[str, Any]:
        ctx = {"latencia_max_ms": 2000, "presupuesto_usd": 1, "accion_irreversible": True, "humano_en_circuito": True}
        bad = self.verifier.verify(ctx)
        return {"meta_innovacion": goal, "verificacion_simbolica": {"aprobado": not bad, "violaciones": bad},
                "plan_strips": strips_plan(), "asignacion_ejemplo": optimize_assignment([5, 3, 8, 2, 7, 4, 6, 1], 3)}

# ---------------- S5: optimizacion (greedy vs recocido simulado) ----------------
def optimize_assignment(durations: List[float], agents: int, iters: int = 4000, seed: int = 0) -> Dict[str, Any]:
    """Minimiza el makespan (carga maxima). Base: LPT greedy; mejora: recocido simulado."""
    rnd = random.Random(seed)
    def cost(a):
        loads = [0.0] * agents
        for d, k in zip(durations, a):
            loads[k] += d
        return max(loads)
    order = sorted(range(len(durations)), key=lambda i: -durations[i])
    loads, greedy = [0.0] * agents, [0] * len(durations)
    for i in order:
        k = loads.index(min(loads)); greedy[i] = k; loads[k] += durations[i]
    cur, best, T = greedy[:], greedy[:], 1.0
    for it in range(iters):
        n = cur[:]; n[rnd.randrange(len(n))] = rnd.randrange(agents)
        dlt = cost(n) - cost(cur)
        if dlt <= 0 or rnd.random() < math.exp(-dlt / max(T, 1e-9)):
            cur = n
            if cost(cur) < cost(best):
                best = cur[:]
        T *= 0.999
    return {"makespan_greedy": cost(greedy), "makespan_sa": cost(best), "asignacion": best}

# ---------------- Anexo A ----------------
def generate_traceability_matrix(topics_csv: str = "config/topics.csv", pages: Optional[Dict[str, str]] = None) -> str:
    pages = pages or {}
    rows = []
    p = Path(topics_csv)
    if p.exists():
        with p.open(encoding="utf-8-sig", newline="") as f:
            rows = [(r["sesion"], r["topico"], r["secciones"]) for r in csv.DictReader(f)]
    else:
        rows = [(k, v["title"], v["secs"]) for k, v in SYLLABUS_MAP.items()]
    out = ["# ANEXO A: Tabla de trazabilidad del syllabus", "",
           "| Sesion | Contenido | Seccion del informe | Pagina | Como se aplica / justificacion si no aplica |", "|---|---|---|---|---|"]
    for ses, top, secs in rows:
        out.append(f"| {ses} | {top} | {secs} | {pages.get(top, '__')} | (completar: aplicacion concreta a la solucion) |")
    return "\n".join(out)

# ---------------- Chequeo del PDF final ----------------
REQUIRED = {"Resumen ejecutivo": r"resumen ejecutivo", "Sec 1": r"problema", "Sec 2": r"modelos fundacionales", "Sec 3": r"aut[oó]noma|gobernanza",
            "Sec 4": r"simb[oó]lic", "Sec 5": r"planificaci[oó]n", "Sec 6": r"optimizaci[oó]n", "Sec 7": r"despliegue", "Sec 8": r"presupuesto",
            "Sec 9": r"factibilidad", "Sec 10": r"estrategia", "Sec 11": r"plan de evaluaci[oó]n", "Sec 12": r"recomendaci[oó]n",
            "Anexo A": r"anexo a", "Anexo B": r"anexo b", "Anexo C": r"anexo c|declaraci[oó]n de uso de ia", "Anexo D": r"anexo d|aportes por integrante"}

def check_pdf(path: str) -> Dict[str, Any]:
    from pypdf import PdfReader
    pages = [(pg.extract_text() or "") for pg in PdfReader(path).pages]
    low = [t.lower() for t in pages]
    first_annex = next((i for i, t in enumerate(low) if re.search(r"anexo a\b", t) and "trazabilidad" in t), len(pages))
    body = first_annex
    missing = [k for k, rx in REQUIRED.items() if not any(re.search(rx, t) for t in low)]
    return {"paginas_total": len(pages), "paginas_sin_anexos": body, "rango_20_35_ok": 20 <= body <= 35,
            "secciones_faltantes": missing, "veredicto_presente": any(re.search(r"viable con condiciones|no viable|\bviable\b", t) for t in low)}

# ---------------- S5: seleccion de portafolio de automatizaciones (mochila) ----------------
PORTAFOLIO_EJEMPLO = [  # ilustrativo: supuestos para una pyme; setup y mensual en USD
    {"nombre": "Planilla de cierre de caja (sin IA)", "setup": 100, "mensual": 0, "ahorro": 150},
    {"nombre": "Bot de reglas para preguntas frecuentes", "setup": 800, "mensual": 30, "ahorro": 400},
    {"nombre": "RAG sobre el manual de la empresa", "setup": 3000, "mensual": 80, "ahorro": 900},
    {"nombre": "ML para predecir abandono de clientes", "setup": 4000, "mensual": 60, "ahorro": 1300},
    {"nombre": "Optimizador de rutas de reparto", "setup": 6000, "mensual": 80, "ahorro": 1500},
    {"nombre": "Agente de agendamiento con humano", "setup": 12000, "mensual": 200, "ahorro": 2600},
]

def select_portfolio(items: List[Dict[str, Any]], budget: float, hours_available: Optional[float] = None) -> Dict[str, Any]:
    """Exact enumeration and greedy baseline, with setup budget, hours and dependency closure.
    Hours are total implementation effort, not a calendar makespan. At most 20 items.
    Optional item keys: horas (nonnegative), depende_de (list of item names).
    """
    if not math.isfinite(budget) or budget < 0 or (hours_available is not None and (not math.isfinite(hours_available) or hours_available < 0)):
        raise ValueError("Presupuesto y horas deben ser finitos y no negativos")
    if len(items) > 20:
        raise ValueError("Enumeracion limitada a 20 candidatas")
    names = [x["nombre"] for x in items]
    if len(set(names)) != len(names):
        raise ValueError("Nombres duplicados")
    by = {x["nombre"]: x for x in items}
    for x in items:
        for k in ("setup", "mensual", "ahorro", "horas"):
            v = x.get(k, 0)
            if not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0:
                raise ValueError("Costos, ahorro y horas deben ser finitos y no negativos")
        if any(d not in by for d in x.get("depende_de", [])):
            raise ValueError("Dependencia inexistente")
    def closure(name, visiting=None):
        visiting = set() if visiting is None else visiting
        if name in visiting:
            raise ValueError("Dependencia circular")
        out = {name}
        for dep in by[name].get("depende_de", []):
            out |= closure(dep, visiting | {name})
        return out
    closures = {n: closure(n) for n in names}
    def feasible(sel):
        chosen = {x["nombre"] for x in sel}
        return (sum(x["setup"] for x in sel) <= budget and
                (hours_available is None or sum(x.get("horas", 0) for x in sel) <= hours_available) and
                all(set(x.get("depende_de", [])) <= chosen for x in sel))
    net = lambda x: x["ahorro"] - x["mensual"]
    exact, best = [], 0.0
    for mask in range(1 << len(items)):
        sel = [x for i, x in enumerate(items) if mask >> i & 1]
        value = sum(net(x) for x in sel)
        if feasible(sel) and value > best:
            exact, best = sel, value
    greedy = []
    for x in sorted(items, key=lambda x: -net(x) / max(x["setup"], 1)):
        wanted = {z["nombre"] for z in greedy} | closures[x["nombre"]]
        sel = [z for z in items if z["nombre"] in wanted]
        if feasible(sel) and sum(net(z) for z in sel) > sum(net(z) for z in greedy):
            greedy = sel
    pack = lambda sel: {"elegidas": [x["nombre"] for x in sel], "setup_usd": sum(x["setup"] for x in sel),
                        "horas": sum(x.get("horas", 0) for x in sel),
                        "beneficio_neto_mensual_usd": sum(net(x) for x in sel)}
    return {"presupuesto_setup_usd": budget, "horas_disponibles": hours_available,
            "combinaciones_evaluadas": 1 << len(items), "exacto": pack(exact), "voraz": pack(greedy)}

# ---------------- CLI ----------------
def run_cli(argv=None):
    ap = argparse.ArgumentParser(description="Magister Copilot TAAI2")
    sp = ap.add_subparsers(dest="cmd")
    sp.add_parser("plan").add_argument("goal")
    b = sp.add_parser("budget")
    b.add_argument("--queries", type=int, default=50000)
    b.add_argument("--strategy", choices=list(STRATEGIES) + ["all"], default="all")
    b.add_argument("--xlsx", help="ruta del Excel Anexo B")
    sp.add_parser("traceability")
    r = sp.add_parser("reliability")
    r.add_argument("--acc", default="0.95,0.9,0.92,0.97")
    r.add_argument("--hitl", default="", help="ej: 3:0.8")
    sp.add_parser("risks")
    pf = sp.add_parser("portfolio"); pf.add_argument("--presupuesto", type=float, default=12000); pf.add_argument("--horas", type=float); pf.add_argument("--json", help="archivo con la lista de automatizaciones")
    o = sp.add_parser("optimize")
    o.add_argument("--agents", type=int, default=3)
    o.add_argument("--durations", default="5,3,8,2,7,4,6,1")
    sp.add_parser("check-pdf").add_argument("pdf")
    a = ap.parse_args(argv)
    dump = lambda x: print(json.dumps(x, indent=2, ensure_ascii=False))
    if a.cmd == "plan": dump(InnovationPlanner().generate_plan(a.goal))
    elif a.cmd == "budget":
        calc = BudgetCalculator(monthly_queries=a.queries)
        strategies = STRATEGIES if a.strategy == "all" else (a.strategy,)
        res = {s: calc.evaluate(s) for s in strategies}
        res["sensibilidad_top3_van36"] = {s: calc.sensitivity(s) for s in strategies}
        if a.xlsx: res["excel"] = calc.export_xlsx(a.xlsx)
        dump(res)
    elif a.cmd == "traceability": print(generate_traceability_matrix())
    elif a.cmd == "reliability":
        h = {int(k): float(v) for k, v in (x.split(":") for x in a.hitl.split(",") if x)}
        dump(chain_reliability([float(x) for x in a.acc.split(",")], h))
    elif a.cmd == "risks": dump(risk_register())
    elif a.cmd == "portfolio":
        items = json.loads(Path(a.json).read_text(encoding="utf-8")) if a.json else PORTAFOLIO_EJEMPLO
        dump(select_portfolio(items, a.presupuesto, a.horas))
    elif a.cmd == "optimize": dump(optimize_assignment([float(x) for x in a.durations.split(",")], a.agents))
    elif a.cmd == "check-pdf": dump(check_pdf(a.pdf))
    else: ap.print_help()

if __name__ == "__main__":
    run_cli()
