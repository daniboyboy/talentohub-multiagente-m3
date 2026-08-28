"""
Corre el golden dataset completo contra el sistema multiagente.

Todas las trazas quedan etiquetadas con el mismo run_tag para poder
compararlas juntas en Langfuse y contra corridas anteriores.

Uso:
    python scripts/run_golden.py golden-run-v1
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.multi_agent_system import atender_consulta, langfuse  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent


def cargar_casos() -> list[dict]:
    """Lee el golden dataset desde disco."""
    ruta = RAIZ / "test_queries.json"
    return json.loads(ruta.read_text(encoding="utf-8"))


def correr_caso(caso: dict, run_tag: str) -> dict:
    """Ejecuta un caso y compara el intent obtenido contra el esperado."""
    resultado = atender_consulta(
        consulta=caso["query"],
        expected_intent=caso["expected_intent"],
        run_tag=run_tag,
    )
    resultado["expected_intent"] = caso["expected_intent"]
    resultado["tipo"] = caso["tipo"]
    resultado["acierto"] = resultado["intent"] == caso["expected_intent"]
    return resultado


def imprimir_resumen(resultados: list[dict]) -> None:
    """Muestra la tabla de resultados y la exactitud de enrutamiento."""
    aciertos = sum(1 for r in resultados if r["acierto"])
    total = len(resultados)

    print(f"\n{'=' * 78}")
    print(f"{'OK':<4}{'ESPERADO':<18}{'OBTENIDO':<18}{'CONSULTA'}")
    print(f"{'=' * 78}")
    for r in resultados:
        marca = "OK" if r["acierto"] else "XX"
        print(
            f"{marca:<4}{r['expected_intent']:<18}{r['intent']:<18}"
            f"{r['query'][:38]}"
        )

    print(f"{'=' * 78}")
    print(f"Routing accuracy: {aciertos}/{total} = {aciertos / total:.1%}")

    fallos = [r for r in resultados if not r["acierto"]]
    if fallos:
        print("\nFallos por tipo de caso:")
        for r in fallos:
            print(f"  [{r['tipo']}] {r['query']}")
            print(f"     trace_id: {r['trace_id']}")


def guardar_resultados(resultados: list[dict], run_tag: str) -> None:
    """Persiste los resultados de la corrida para comparaciones posteriores."""
    destino = RAIZ / "outputs" / f"{run_tag}.json"
    destino.parent.mkdir(exist_ok=True)
    destino.write_text(
        json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nResultados guardados en {destino}")


if __name__ == "__main__":
    etiqueta = sys.argv[1] if len(sys.argv) > 1 else "golden-run-v1"
    casos = cargar_casos()
    print(f"Corriendo {len(casos)} casos con tag '{etiqueta}'...\n")

    resultados = []
    for numero, caso in enumerate(casos, start=1):
        print(f"  {numero}/{len(casos)}: {caso['query'][:50]}")
        resultados.append(correr_caso(caso, etiqueta))

    langfuse.flush()
    imprimir_resumen(resultados)
    guardar_resultados(resultados, etiqueta)
