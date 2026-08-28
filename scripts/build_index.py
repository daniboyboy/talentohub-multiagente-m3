"""
Construye el indice vectorial de un dominio a partir de sus documentos.

Uso:
    python scripts/build_index.py hr
    python scripts/build_index.py tech
    python scripts/build_index.py finance
"""

import sys
from pathlib import Path

import tiktoken
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

RAIZ = Path(__file__).resolve().parent.parent
EMBEDDING_MODEL = "text-embedding-3-small"
MAX_TOKENS_POR_CHUNK = 500
MIN_CHUNKS_POR_DOMINIO = 50


def contar_tokens(texto: str) -> int:
    """Cuenta tokens con el mismo tokenizador que usa el modelo de embeddings."""
    return len(tiktoken.get_encoding("cl100k_base").encode(texto))


def extraer_seccion(bloque: str) -> str:
    """Devuelve la etiqueta [Seccion] del inicio del bloque, o 'General'."""
    if bloque.startswith("[") and "]" in bloque:
        return bloque[1:bloque.index("]")]
    return "General"


def leer_bloques(ruta_archivo: Path, dominio: str) -> list[Document]:
    """Parte un archivo en bloques Q&A y los convierte en Documents con metadata."""
    texto = ruta_archivo.read_text(encoding="utf-8")
    bloques = [b.strip() for b in texto.split("\n\n") if b.strip().startswith("[")]
    return [
        Document(
            page_content=bloque,
            metadata={
                "dominio": dominio,
                "fuente": ruta_archivo.name,
                "seccion": extraer_seccion(bloque),
            },
        )
        for bloque in bloques
    ]


def aplicar_salvaguarda(documentos: list[Document]) -> list[Document]:
    """Subdivide solo los bloques que superan el limite de tokens."""
    divisor = RecursiveCharacterTextSplitter(
        chunk_size=MAX_TOKENS_POR_CHUNK * 4,
        chunk_overlap=50,
        length_function=len,
    )
    resultado = []
    for doc in documentos:
        if contar_tokens(doc.page_content) > MAX_TOKENS_POR_CHUNK:
            resultado.extend(divisor.split_documents([doc]))
        else:
            resultado.append(doc)
    return resultado


def cargar_dominio(dominio: str) -> list[Document]:
    """Lee todos los documentos de un dominio y devuelve los chunks listos."""
    carpeta = RAIZ / "data" / f"{dominio}_docs"
    if not carpeta.exists():
        raise SystemExit(f"No existe la carpeta {carpeta}")

    documentos = []
    for archivo in sorted(carpeta.glob("*.md")):
        bloques = leer_bloques(archivo, dominio)
        print(f"  {archivo.name}: {len(bloques)} bloques")
        documentos.extend(bloques)
    return aplicar_salvaguarda(documentos)


def construir_indice(dominio: str) -> None:
    """Embebe los chunks del dominio y guarda el indice en disco."""
    print(f"\nDominio: {dominio}")
    chunks = cargar_dominio(dominio)
    print(f"  TOTAL: {len(chunks)} chunks")

    if len(chunks) < MIN_CHUNKS_POR_DOMINIO:
        raise SystemExit(
            f"ERROR: {len(chunks)} chunks, se requieren {MIN_CHUNKS_POR_DOMINIO}"
        )

    almacen = InMemoryVectorStore(OpenAIEmbeddings(model=EMBEDDING_MODEL))
    almacen.add_documents(chunks)

    destino = RAIZ / "indexes" / f"{dominio}.json"
    destino.parent.mkdir(exist_ok=True)
    almacen.dump(str(destino))
    print(f"  Indice guardado en {destino}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Uso: python scripts/build_index.py <dominio>")
    construir_indice(sys.argv[1])
