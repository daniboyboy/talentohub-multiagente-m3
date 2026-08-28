"""
Prueba la recuperacion de un indice ya construido, sin llamar al LLM.

Uso:
    python scripts/test_retrieval.py hr
"""

import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import OpenAIEmbeddings

load_dotenv()

RAIZ = Path(__file__).resolve().parent.parent
EMBEDDING_MODEL = "text-embedding-3-small"
K = 3

CONSULTAS = {
    "hr": [
        "cuantos dias de vacaciones tengo",
        "mi pareja va a tener un bebe, que licencia me dan",
        "me equivocaron el pago de la quincena",
    ],
    "tech": [
        "no me conecta la vpn",
        "olvide mi contrasena",
        "necesito instalar un programa nuevo",
    ],
    "finance": [
        "cuando me reembolsan los gastos de viaje",
        "como radico una factura de proveedor",
        "necesito un anticipo para un viaje",
    ],
}


def cargar_indice(dominio: str) -> InMemoryVectorStore:
    """Carga desde disco el indice del dominio."""
    ruta = RAIZ / "indexes" / f"{dominio}.json"
    if not ruta.exists():
        raise SystemExit(f"No existe {ruta}. Corre primero build_index.py")
    return InMemoryVectorStore.load(
        str(ruta), OpenAIEmbeddings(model=EMBEDDING_MODEL)
    )


def probar(dominio: str) -> None:
    """Corre las consultas de prueba y muestra los chunks recuperados."""
    almacen = cargar_indice(dominio)
    for consulta in CONSULTAS[dominio]:
        print(f"\n{'=' * 70}\nCONSULTA: {consulta}\n{'=' * 70}")
        resultados = almacen.similarity_search_with_score(consulta, k=K)
        for posicion, (doc, puntaje) in enumerate(resultados, start=1):
            seccion = doc.metadata["seccion"]
            fuente = doc.metadata["fuente"]
            primera_linea = doc.page_content.split("\n")[0]
            print(f"\n{posicion}. [{puntaje:.4f}] {seccion} | {fuente}")
            print(f"   {primera_linea}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Uso: python scripts/test_retrieval.py <dominio>")
    probar(sys.argv[1])
