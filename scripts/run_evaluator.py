"""
Evalua las respuestas de una corrida del golden dataset y registra los
puntajes en Langfuse asociados a la traza de cada consulta.

Lee los resultados ya guardados (consulta, respuesta y trace_id), asi que no
vuelve a ejecutar el pipeline completo: una llamada al LLM por caso.

Uso:
    python scripts/run_evaluator.py golden-run-v1
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.evaluator import evaluar_y_registrar, langfuse  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent


def cargar_corrida(etiqueta: str) -> list[dict]:
    """Lee los resultados guardados de una corrida del golden dataset."""
    ruta = RAIZ / "outputs" / f"{etiqueta}.json"
    if not ruta.exists():
        raise SystemExit(f"No existe {ruta}. Corre primero scripts/run_golden.py")
    return json.loads(ruta.read_text(encoding="utf-8"))


def imprimir_resumen(evaluados: list[dict]) -> None:
    """Muestra los puntajes por caso y el promedio general."""
    print(f"\n{'=' * 84}")
    print(f"{'PUNTAJE':<10}{'REL':<6}{'COM':<6}{'PRE':<6}CONSULTA")
    print(f"{'=' * 84}")
    for e in evaluados:
        print(
            f"{e['puntaje']:<10}{e['relevancia']:<6}{e['completitud']:<6}"
            f"{e['precision']:<6}{e['query'][:44]}"
        )

    promedio = sum(e["puntaje"] for e in evaluados) / len(evaluados)
    print(f"{'=' * 84}")
    print(f"Puntaje promedio: {promedio:.2f}/10 sobre {len(evaluados)} respuestas")

    bajos = sorted(evaluados, key=lambda e: e["puntaje"])[:3]
    print("\nRespuestas peor puntuadas:")
    for e in bajos:
        print(f"  [{e['puntaje']}/10] {e['query']}")
        print(f"        {e['justificacion']}")


def guardar(evaluados: list[dict], etiqueta: str) -> None:
    """Persiste las evaluaciones junto a los resultados de la corrida."""
    destino = RAIZ / "outputs" / f"{etiqueta}-evaluacion.json"
    destino.write_text(
        json.dumps(evaluados, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nEvaluaciones guardadas en {destino}")


if __name__ == "__main__":
    etiqueta = sys.argv[1] if len(sys.argv) > 1 else "golden-run-v1"
    casos = cargar_corrida(etiqueta)
    print(f"Evaluando {len(casos)} respuestas de '{etiqueta}'...\n")

    evaluados = []
    for numero, caso in enumerate(casos, start=1):
        print(f"  {numero}/{len(casos)}: {caso['query'][:50]}")
        evaluacion = evaluar_y_registrar(
            query=caso["query"],
            response=caso["response"],
            trace_id=caso["trace_id"],
        )
        evaluados.append({**caso, **evaluacion.model_dump()})

    langfuse.flush()
    imprimir_resumen(evaluados)
    guardar(evaluados, etiqueta)
