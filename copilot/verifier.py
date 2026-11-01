import re
from typing import List, Dict, Any, Tuple

class GroundingVerifier:
    """
    Verificador neuro-simbólico:
    1. Asegura que las citas [X] generadas existan en los fragmentos de contexto.
    2. Valida consistencia de restricciones de precedencia (detección de ciclos).
    """
    @staticmethod
    def verify_citations(response_text: str, context_chunks: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        valid_indices = {str(i + 1) for i in range(len(context_chunks))}
        cited_indices = set(re.findall(r"\[(\d+)\]", response_text))
        
        hallucinated_citations = cited_indices - valid_indices
        is_grounded = len(hallucinated_citations) == 0 and len(cited_indices) > 0
        
        errors = [f"Cita inexistente [{c}] detectada." for c in hallucinated_citations]
        return is_grounded, errors

    @staticmethod
    def validate_precedence_graph(tasks: List[Dict[str, Any]]) -> Tuple[bool, str]:
        # Algoritmo de detección de ciclos de dependencias
        adj = {t["id"]: t.get("depends_on", []) for t in tasks}
        visited = {}

        def has_cycle(v):
            visited[v] = 1  # en progreso
            for neighbor in adj.get(v, []):
                if visited.get(neighbor) == 1:
                    return True
                if visited.get(neighbor) == 0 and has_cycle(neighbor):
                    return True
            visited[v] = 2  # completado
            return False

        for node in adj:
            visited[node] = 0

        for node in adj:
            if visited[node] == 0:
                if has_cycle(node):
                    return False, f"Ciclo de dependencia circular detectado involucrando la tarea '{node}'."
        return True, "Grafo de dependencias válido y acíclico."