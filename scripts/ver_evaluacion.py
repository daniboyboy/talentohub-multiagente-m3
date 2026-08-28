import json
import sys
from pathlib import Path

etiqueta = sys.argv[1] if len(sys.argv) > 1 else "golden-run-v1"
ruta = Path("outputs") / f"{etiqueta}-evaluacion.json"
datos = json.loads(ruta.read_text(encoding="utf-8"))

promedio = sum(e["puntaje"] for e in datos) / len(datos)
print(f"Puntaje promedio: {promedio:.2f}/10 sobre {len(datos)} respuestas\n")

print(f"{'PTS':<5}{'REL':<5}{'COM':<5}{'PRE':<5}CONSULTA")
print("-" * 80)
for e in sorted(datos, key=lambda x: x["puntaje"]):
    print(
        f"{e['puntaje']:<5}{e['relevancia']:<5}{e['completitud']:<5}"
        f"{e['precision']:<5}{e['query'][:50]}"
    )

print("\nTres peores, con la justificacion del evaluador:")
for e in sorted(datos, key=lambda x: x["puntaje"])[:3]:
    print(f"\n  [{e['puntaje']}/10] {e['query']}")
    print(f"  {e['justificacion']}")