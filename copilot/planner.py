"""Paso 7: reparto de secciones y calendario de 14 días (heurística voraz con dependencias).

Es una línea base para la tarea del grupo y, si lo desean, evidencia para las secciones 5 y 6 del informe:
el siguiente paso natural es reemplazarla por un solver (CP-SAT, ILP) y comparar los resultados.

Supuestos del modelo (todos editables aquí o en config/*.csv):
- Cada sección tiene un responsable y puede recibir apoyo de UNA persona más, que rinde HELPER_EFFICIENCY.
- Una sección no empieza hasta que terminan las secciones de las que depende (día siguiente).
- La disponibilidad distingue días hábiles y fines de semana.
"""

import csv
from datetime import date, timedelta
from pathlib import Path

from . import defaults as D

DAYS = 14
START = date(2026, 10, 26)  # día 1 = lunes 26-oct-2026; día 14 = domingo 8-nov-2026
PREFERENCE_BONUS = 0.25  # fracción de las horas que "descuenta" asignar una sección a quien tiene esa fortaleza
HELPER_EFFICIENCY = 0.7
SECTION_FIELDS = ["id", "seccion", "horas", "depende_de", "dia_limite", "perfil"]
TEAM_FIELDS = ["nombre", "horas_dia_habil", "horas_fin_de_semana", "fortalezas", "dias_sin_disponibilidad"]


def write_defaults(config_dir):
    config_dir = Path(config_dir)
    config_dir.mkdir(parents=True, exist_ok=True)
    for name, fields, data in (("sections.csv", SECTION_FIELDS, D.SECTIONS), ("team.csv", TEAM_FIELDS, D.TEAM)):
        p = config_dir / name
        if not p.exists():
            with open(p, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f)
                w.writerow(fields)
                w.writerows(data)


def _read(path, fields, default):
    p = Path(path)
    if not p.exists():
        return [dict(zip(fields, row)) for row in default]
    with open(p, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _split(s):
    return [x.strip() for x in (s or "").split(";") if x.strip()]


def day_capacity(member, d):
    off = {int(x) for x in _split(member["dias_sin_disponibilidad"])}
    if d in off:
        return 0.0
    weekend = (START + timedelta(days=d - 1)).weekday() >= 5
    return float(member["horas_fin_de_semana"] if weekend else member["horas_dia_habil"])


def topo_order(sections):
    by_id = {s["id"]: s for s in sections}
    order, seen, visiting = [], set(), set()

    def visit(sid):
        if sid in seen:
            return
        if sid in visiting:
            raise SystemExit(f"Dependencia circular en sections.csv alrededor de {sid}")
        visiting.add(sid)
        for d in _split(by_id[sid]["depende_de"]):
            if d not in by_id:
                raise SystemExit(f"{sid} depende de '{d}', que no existe en sections.csv")
            visit(d)
        visiting.discard(sid)
        seen.add(sid)
        order.append(sid)

    for s in sorted(sections, key=lambda s: (int(s["dia_limite"]), s["id"])):
        visit(s["id"])
    return [by_id[i] for i in order]


def assign(sections, team):
    load = {m["nombre"]: 0.0 for m in team}
    cap = {m["nombre"]: sum(day_capacity(m, d) for d in range(1, DAYS + 1)) for m in team}
    strengths = {m["nombre"]: set(_split(m["fortalezas"])) for m in team}
    owner = {}
    for s in sorted(sections, key=lambda s: -float(s["horas"])):
        h = float(s["horas"])

        def cost(name):
            bonus = PREFERENCE_BONUS * h if s["perfil"] in strengths[name] else 0.0
            return (load[name] + h - bonus) / max(cap[name], 0.1)

        best = min(load, key=cost)
        owner[s["id"]] = best
        load[best] += h
    return owner, load, cap


def schedule(sections, owner, team):
    free = {m["nombre"]: {d: day_capacity(m, d) for d in range(1, DAYS + 1)} for m in team}
    spent = {m["nombre"]: 0.0 for m in team}
    end, rows = {}, []
    for s in topo_order(sections):
        who = owner[s["id"]]
        deps = _split(s["depende_de"])
        day = max([end[d] for d in deps] + [0]) + 1
        remaining, start, last, helper = float(s["horas"]), None, None, None
        while remaining > 1e-9 and day <= DAYS:
            use = min(free[who][day], remaining)
            if use > 0:
                free[who][day] -= use
                spent[who] += use
                remaining -= use
                start, last = start or day, day
            if remaining > 1e-9:
                cands = [n for n in free if n != who and free[n][day] > 0 and (helper is None or n == helper)]
                if cands:
                    h = max(cands, key=lambda n: free[n][day])
                    spend = min(free[h][day], remaining / HELPER_EFFICIENCY)
                    free[h][day] -= spend
                    spent[h] += spend
                    remaining -= spend * HELPER_EFFICIENCY
                    helper = h
                    start, last = start or day, day
            day += 1
        overflow = remaining > 1e-9
        end[s["id"]] = DAYS + 1 if overflow else last
        rows.append({
            "id": s["id"], "seccion": s["seccion"], "responsable": who, "apoyo": helper or "",
            "horas": s["horas"], "inicio_dia": start or "-", "fin_dia": "NO CABE" if overflow else last,
            "dia_limite": s["dia_limite"],
            "alerta": "no cabe en 14 días" if overflow else
                      ("termina después del día límite" if last > int(s["dia_limite"]) else ""),
        })
    return rows, spent


def plan(config_dir):
    sections = _read(Path(config_dir) / "sections.csv", SECTION_FIELDS, D.SECTIONS)
    team = _read(Path(config_dir) / "team.csv", TEAM_FIELDS, D.TEAM)
    owner, load, cap = assign(sections, team)
    rows, spent = schedule(sections, owner, team)
    return rows, load, cap, spent


def render(rows, load, cap, spent):
    lines = ["# Reparto y calendario (heurística)", "",
             "Día 1 = lun 26-oct-2026; día 14 = dom 8-nov-2026. Fines de semana: días 6, 7, 13 y 14.", "",
             "| Sección | Responsable | Apoyo | Horas | Inicio | Fin | Límite | Alerta |", "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['seccion']} | {r['responsable']} | {r['apoyo'] or '-'} | {r['horas']} | {r['inicio_dia']} | "
                     f"{r['fin_dia']} | {r['dia_limite']} | {r['alerta']} |")
    lines += ["", "| Integrante | Horas como responsable | Horas trabajadas | Capacidad (14 días) | Uso |", "|---|---|---|---|---|"]
    for name in load:
        lines.append(f"| {name} | {load[name]:.0f} | {spent[name]:.0f} | {cap[name]:.0f} | "
                     f"{100 * spent[name] / max(cap[name], 0.1):.0f}% |")
    alerts = [r for r in rows if r["alerta"]]
    lines += ["", ("Atención: " + str(len(alerts)) + " sección(es) con alerta; hay que subir disponibilidad, bajar alcance "
                   "o reordenar dependencias.") if alerts else "Todas las secciones caben antes de su día límite.",
              "", "Las horas por sección y la disponibilidad son supuestos: ajústenlos en config/sections.csv y config/team.csv."]
    return "\n".join(lines)
