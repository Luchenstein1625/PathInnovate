"""Complementos de presupuesto (S6): supuestos desde mediciones, punto de equilibrio de volumen,
sensibilidad con variables independientes y escenario de precios -10x. Anexo B honesto con fechas."""
from dataclasses import replace
from typing import Any, Dict, List, Optional

from copilot.engine_taai2 import Assumptions, BudgetCalculator, STRATEGIES


def from_measurements(base: Assumptions, prompt_tokens: float, completion_tokens: float, latency_s: float,
                      in_price: float, out_price: float, utilization: float = 0.3, always_on: bool = False) -> Assumptions:
    """Tokens por consulta, precios y horas de GPU (consultas x latencia / utilizacion) tomados de la corrida."""
    hours = 730.0 if always_on else max(1.0, base.monthly_queries * latency_s / 3600 / utilization)
    return replace(base, prompt_tokens=int(round(prompt_tokens)), completion_tokens=int(round(completion_tokens)),
                   api_in_per_mtok=in_price, api_out_per_mtok=out_price, gpu_hours_month=round(hours, 1))


def breakeven_volume(a: Assumptions, months: int = 36) -> Optional[float]:
    """Consultas/mes desde las que el SLM propio (GPU fija) cuesta menos que la API."""
    var = (a.prompt_tokens * a.api_in_per_mtok + a.completion_tokens * a.api_out_per_mtok) / 1e6
    if var <= 0:
        return None
    self_fixed = a.gpu_hour * a.gpu_hours_month + a.infra_base_month + a.personnel_self + a.capex_self / months
    api_fixed = 50.0 + a.personnel_api + a.capex_api / months
    return max(0.0, (self_fixed - api_fixed) / var)


_VARS = ("monthly_queries", "prompt_tokens", "completion_tokens", "api_in_per_mtok", "api_out_per_mtok", "gpu_hour",
         "gpu_hours_month", "personnel_api", "personnel_self", "personnel_hybrid", "capex_api", "capex_self",
         "capex_hybrid", "slm_share_hybrid")


def tornado(a: Assumptions, strategy: str, delta: float = 0.3, months: int = 36, top: int = 3) -> List[Dict[str, Any]]:
    """Sensibilidad del TCO (no del VAN, que depende de un beneficio no medido). Una variable a la vez."""
    out = []
    for v in _VARS:
        lo, hi = [BudgetCalculator(assumptions=replace(a, **{v: getattr(a, v) * f})).compute_tco(months, strategy)["tco_total_usd"]
                  for f in (1 - delta, 1 + delta)]
        if abs(hi - lo) > 0.005:
            out.append({"variable": v, "tco_bajo": lo, "tco_alto": hi, "oscilacion": round(abs(hi - lo), 2)})
    return sorted(out, key=lambda x: -x["oscilacion"])[:top]


def price_drop(a: Assumptions, factor: float = 10.0, months: int = 36) -> Dict[str, Any]:
    cheap = replace(a, api_in_per_mtok=a.api_in_per_mtok / factor, api_out_per_mtok=a.api_out_per_mtok / factor)
    res = {s: {"tco_actual": BudgetCalculator(assumptions=a).compute_tco(months, s)["tco_total_usd"],
               "tco_precios_div": BudgetCalculator(assumptions=cheap).compute_tco(months, s)["tco_total_usd"]} for s in STRATEGIES}
    return {"factor": factor, "meses": months, "estrategias": res, "volumen_equilibrio_actual": breakeven_volume(a, months),
            "volumen_equilibrio_nuevo": breakeven_volume(cheap, months)}


def tco_for_dashboard(a: Assumptions, months: int = 12) -> Dict[str, Any]:
    c = BudgetCalculator(assumptions=a)
    return {"meses": months, "supuestos": {k: v for k, v in a.__dict__.items()},
            "estrategias": {s: c.compute_tco(months, s) for s in STRATEGIES},
            "equilibrio_consultas_mes": breakeven_volume(a), "precio_x10_menos": price_drop(a)}


def export_anexo_b(a: Assumptions, path: str, medidos: Optional[Dict[str, str]] = None,
                   verificados: Optional[Dict[str, tuple]] = None, fecha_corrida: str = "") -> str:
    """medidos: {variable: 'detalle'}; verificados: {variable: (fuente_url, 'AAAA-MM-DD')}.
    Lo no verificado queda como SUPUESTO sin fecha: no se estampa una fecha de consulta falsa."""
    from openpyxl import Workbook
    medidos, verificados = medidos or {}, verificados or {}
    calc = BudgetCalculator(assumptions=a)
    wb = Workbook(); ws = wb.active; ws.title = "Supuestos"
    ws.append(["Variable", "Valor", "Fuente / supuesto", "Fecha consulta"])
    for k, v in a.__dict__.items():
        if k in verificados:
            ws.append([k, v, verificados[k][0], verificados[k][1]])
        elif k in medidos:
            ws.append([k, v, "Medido en la corrida: " + medidos[k], fecha_corrida])
        else:
            ws.append([k, v, "SUPUESTO del grupo (sin fuente verificada)", "—"])
    t = wb.create_sheet("TCO"); t.append(["Estrategia", "Meses", "CAPEX", "OPEX", "TCO", "VAN", "Equilibrio (mes)"])
    for s in STRATEGIES:
        for m in (12, 36):
            c = calc.compute_tco(m, s); r = t.max_row + 1
            t.append([s, m, c["capex_usd"], c["opex_usd"], f"=C{r}+D{r}", calc.npv(m, s), calc.break_even_month(s)])
    sn = wb.create_sheet("Sensibilidad_TCO36"); sn.append(["Estrategia", "Variable", "TCO -30%", "TCO +30%", "Oscilación"])
    for s in STRATEGIES:
        for x in tornado(a, s):
            sn.append([s, x["variable"], x["tco_bajo"], x["tco_alto"], x["oscilacion"]])
    e = wb.create_sheet("Equilibrio"); e.append(["Consultas/mes de equilibrio API vs SLM propio", breakeven_volume(a)])
    d = price_drop(a); x = wb.create_sheet("Escenario_precios_div10"); x.append(["Estrategia", "TCO36 actual", "TCO36 precios/10"])
    for s, v in d["estrategias"].items():
        x.append([s, v["tco_actual"], v["tco_precios_div"]])
    wb.save(path); return path
