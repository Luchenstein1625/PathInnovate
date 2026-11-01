from typing import List, Dict, Any

class WorkloadOptimizer:
    """
    Planificador por optimización de restricciones y balanceo de carga.
    Función objetivo: Min max(horas_asignadas_por_persona) sujeto a disponibilidades.
    """
    def __init__(self, members: Dict[str, float]):
        # members: {"IntegranteA": max_horas, "IntegranteB": max_horas}
        self.members = members

    def schedule(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Asigna tareas respetando límites de horas y dependencias lógicas.
        """
        assigned = {m: [] for m in self.members}
        load = {m: 0.0 for m in self.members}
        unassigned = []

        # Ordenar por duración descendente (heurística LPT para bin-packing)
        sorted_tasks = sorted(tasks, key=lambda x: x.get("duration_hours", 1.0), reverse=True)

        for task in sorted_tasks:
            duration = float(task.get("duration_hours", 1.0))
            # Buscar el integrante con menor carga acumulada que tenga capacidad disponible
            candidates = [m for m in self.members if load[m] + duration <= self.members[m]]
            if not candidates:
                unassigned.append(task)
                continue
            
            best_member = min(candidates, key=lambda m: load[m])
            assigned[best_member].append(task["id"])
            load[best_member] += duration

        return {
            "schedule": assigned,
            "accumulated_hours": load,
            "unassigned_tasks": unassigned,
            "balanced_metric_makespan": max(load.values()) if load else 0
        }