"""
Prueba el sistema multiagente con una consulta suelta.

Uso:
    python scripts/run_query.py "no me conecta la vpn"
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.multi_agent_system import atender_consulta, langfuse  # noqa: E402

if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit('Uso: python scripts/run_query.py "tu consulta"')

    resultado = atender_consulta(" ".join(sys.argv[1:]))
    langfuse.flush()

    print(f"\nCONSULTA : {resultado['query']}")
    print(f"INTENT   : {resultado['intent']}")
    print(f"TRACE ID : {resultado['trace_id']}")
    print(f"\nRESPUESTA:\n{resultado['response']}")
