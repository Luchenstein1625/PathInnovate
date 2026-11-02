"""Optimizador de cronograma: respeta dependencias, calcula el makespan REAL (tiempo de calendario)
y lo compara con una solucion exacta por enumeracion (n pequeno)."""
import itertools
from typing import Any, Dict, List, Optional


def _topo(tasks: List[Dict[str, Any]]) -> Optional[List[str]]:
    deps = {t["id"]: set(t.get("depends_on", [])) for t in tasks}
    out, ready = [], sorted(i for i, d in deps.items() if not d)
    while ready:
        n = ready.pop(0); out.append(n)
        for i, d in deps.items():
            if n in d:
                d.discard(n)
                if not d and i not in out and i not in ready:
                    ready.append(i)
    return out if len(out) == len(tasks) else None  # None => ciclo


def _tail(tasks):
    """Camino critico restante desde cada tarea (prioridad de despacho)."""
    dur = {t["id"]: float(t.get("duration_hours", 1.0)) for t in tasks}
    succ = {i: [t["id"] for t in tasks if i in t.get("depends_on", [])] for i in dur}
    memo = {}
    def f(i):
        if i not in memo:
            memo[i] = dur[i] + max((f(s) for s in succ[i]), default=0.0)
        return memo[i]
    return {i: f(i) for i in dur}


def _simulate(tasks, assign: Dict[str, str], order: List[str]):
    dur = {t["id"]: float(t.get("duration_hours", 1.0)) for t in tasks}
    deps = {t["id"]: t.get("depends_on", []) for t in tasks}
    free, end, start = {}, {}, {}
    for i in order:
        m = assign[i]
        s = max([free.get(m, 0.0)] + [end[d] for d in deps[i]])
        start[i], end[i], free[m] = s, s + dur[i], s + dur[i]
    return start, end, (max(end.values()) if end else 0.0)


class WorkloadOptimizer:
    """members: {nombre: horas_maximas}. Objetivo: minimizar el makespan (fin de la ultima tarea)
    sujeto a precedencias y a la capacidad de horas de cada integrante."""

    def __init__(self, members: Dict[str, float]):
        self.members = members

    def schedule(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        order0 = _topo(tasks)
        if order0 is None:
            raise ValueError("Las dependencias contienen un ciclo.")
        tail = _tail(tasks)
        dur = {t["id"]: float(t.get("duration_hours", 1.0)) for t in tasks}
        deps = {t["id"]: t.get("depends_on", []) for t in tasks}
        load = {m: 0.0 for m in self.members}; free = {m: 0.0 for m in self.members}
        assign, start, end, unassigned, done = {}, {}, {}, [], set()
        pending = list(order0)
        while pending:
            ready = [i for i in pending if all(d in done or d in [u["id"] for u in unassigned] for d in deps[i])]
            i = max(ready, key=lambda x: tail[x])           # camino critico primero
            pending.remove(i)
            if any(d not in end for d in deps[i]):          # depende de algo sin asignar
                unassigned.append(next(t for t in tasks if t["id"] == i)); continue
            cand = [m for m in self.members if load[m] + dur[i] <= self.members[m]]
            if not cand:
                unassigned.append(next(t for t in tasks if t["id"] == i)); continue
            m = min(cand, key=lambda m: max(free[m], max([end[d] for d in deps[i]], default=0.0)))
            s = max(free[m], max([end[d] for d in deps[i]], default=0.0))
            assign[i], start[i], end[i] = m, s, s + dur[i]
            free[m] = end[i]; load[m] += dur[i]; done.add(i)
        sched = {m: [i for i in assign if assign[i] == m] for m in self.members}
        return {"schedule": sched, "assignment": assign, "start": start, "end": end,
                "accumulated_hours": load, "unassigned_tasks": unassigned,
                "makespan_hours": max(end.values()) if end else 0.0,          # tiempo de calendario
                "balanced_metric_makespan": max(load.values()) if load else 0.0,  # max carga (compat.)
                "critical_path_hours": max(tail.values()) if tail else 0.0}      # cota inferior

    def exact(self, tasks: List[Dict[str, Any]], max_tasks: int = 10) -> Dict[str, Any]:
        """Optimo sobre todas las asignaciones (despacho en orden topologico). n <= max_tasks."""
        if len(tasks) > max_tasks:
            raise ValueError("Demasiadas tareas para enumerar.")
        order = _topo(tasks)
        if order is None:
            raise ValueError("Ciclo.")
        dur = {t["id"]: float(t.get("duration_hours", 1.0)) for t in tasks}
        ids, best = [t["id"] for t in tasks], (float("inf"), None)
        for combo in itertools.product(self.members, repeat=len(ids)):
            assign = dict(zip(ids, combo))
            if any(sum(dur[i] for i in ids if assign[i] == m) > cap for m, cap in self.members.items()):
                continue
            ms = _simulate(tasks, assign, order)[2]
            if ms < best[0]:
                best = (ms, assign)
        return {"makespan_hours": best[0], "assignment": best[1]}
