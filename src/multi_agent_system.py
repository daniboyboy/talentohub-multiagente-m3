"""
Sistema multiagente de soporte interno de TalentoHub.

Un orquestador clasifica la intencion de la consulta mediante function calling
y enruta a uno de tres agentes RAG especializados (HR, IT, Finanzas).
Todo el flujo queda trazado en Langfuse.
"""

from pathlib import Path

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.tools import tool
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langfuse import get_client, propagate_attributes
from langfuse.langchain import CallbackHandler

load_dotenv()

RAIZ = Path(__file__).resolve().parent.parent
EMBEDDING_MODEL = "text-embedding-3-small"
CHAT_MODEL = "gpt-4o-mini"
K = 3

langfuse = get_client()
handler = CallbackHandler()

PROMPT_RAG = ChatPromptTemplate.from_template(
    """Eres un asistente de soporte interno de TalentoHub, especializado en {dominio}.

Responde la pregunta del empleado usando UNICAMENTE la informacion del contexto.
Si el contexto no contiene la respuesta, dilo explicitamente y sugiere el canal
adecuado. No inventes politicas, plazos ni montos.
Responde en espanol, de forma breve y concreta.

Contexto:
{context}

Pregunta: {question}

Respuesta:"""
)

PROMPT_ORQUESTADOR = """Eres el orquestador del sistema de soporte interno de TalentoHub.

Tu unica funcion es clasificar la consulta del empleado y delegarla a la
herramienta del area correspondiente. No respondas con conocimiento propio.

- Consultas sobre empleo, vacaciones, licencias, nomina, beneficios, desempeno,
  contratacion o retiro: usa consultar_recursos_humanos.
- Consultas sobre equipos, accesos, contrasenas, VPN, software, redes,
  seguridad informatica o desarrollo: usa consultar_tecnologia.
- Consultas sobre reembolsos, viaticos, compras, facturas de proveedores,
  presupuesto, contratos o pagos: usa consultar_finanzas.

Si la consulta mezcla dos areas, elige la que resuelva la necesidad principal.
Si no corresponde a ninguna area, no llames ninguna herramienta: pide al
empleado que aclare su solicitud.

Devuelve la respuesta de la herramienta al empleado sin agregar informacion."""

DOMINIOS = {
    "hr": "Recursos Humanos",
    "tech": "Tecnologia",
    "finance": "Finanzas",
}


def cargar_retriever(dominio: str):
    """Carga el indice del dominio desde disco y lo expone como retriever."""
    ruta = RAIZ / "indexes" / f"{dominio}.json"
    if not ruta.exists():
        raise SystemExit(f"Falta {ruta}. Corre scripts/build_index.py {dominio}")
    almacen = InMemoryVectorStore.load(
        str(ruta), OpenAIEmbeddings(model=EMBEDDING_MODEL)
    )
    return almacen.as_retriever(search_kwargs={"k": K})


def formatear_contexto(documentos) -> str:
    """Concatena los chunks recuperados en un bloque de texto para el prompt."""
    return "\n\n".join(doc.page_content for doc in documentos)


def crear_cadena_rag(dominio: str):
    """Arma la cadena LCEL retriever -> prompt -> modelo -> texto."""
    retriever = cargar_retriever(dominio)
    modelo = ChatOpenAI(model=CHAT_MODEL, temperature=0)
    return (
        {
            "context": retriever | formatear_contexto,
            "question": RunnablePassthrough(),
            "dominio": lambda _: DOMINIOS[dominio],
        }
        | PROMPT_RAG
        | modelo
        | StrOutputParser()
    )


CADENAS = {dominio: crear_cadena_rag(dominio) for dominio in DOMINIOS}


def ejecutar_agente(dominio: str, consulta: str) -> str:
    """Corre la cadena del dominio dentro de su propio span de Langfuse."""
    with langfuse.start_as_current_observation(
        as_type="span",
        name=f"{dominio}-agent",
        input={"query": consulta},
    ) as span:
        respuesta = CADENAS[dominio].invoke(consulta, config={"callbacks": [handler]})
        span.update(output={"response": respuesta})
    return respuesta


@tool
def consultar_recursos_humanos(consulta: str) -> str:
    """Responde consultas de Recursos Humanos de TalentoHub: vacaciones, licencias,
    incapacidades, nomina y su calendario de pago, beneficios, medicina prepagada,
    evaluacion de desempeno, plan de carrera, onboarding, certificados laborales,
    renuncia y liquidacion."""
    return ejecutar_agente("hr", consulta)


@tool
def consultar_tecnologia(consulta: str) -> str:
    """Responde consultas de Tecnologia de TalentoHub: contrasenas, accesos y
    permisos, autenticacion de dos factores, VPN, correo, equipos de computo y su
    soporte, instalacion de software, redes y wifi, seguridad de la informacion,
    repositorios de codigo, ambientes e infraestructura."""
    return ejecutar_agente("tech", consulta)


@tool
def consultar_finanzas(consulta: str) -> str:
    """Responde consultas de Finanzas de TalentoHub: reembolso de gastos, viaticos
    y anticipos de viaje, tarjeta corporativa, ordenes de compra y proveedores,
    facturacion y cuentas por pagar, presupuesto y centros de costo, cierre
    contable, contratos y controles financieros."""
    return ejecutar_agente("finance", consulta)


HERRAMIENTAS = [consultar_recursos_humanos, consultar_tecnologia, consultar_finanzas]

TOOL_A_INTENT = {
    "consultar_recursos_humanos": "hr",
    "consultar_tecnologia": "tech",
    "consultar_finanzas": "finance",
}

orquestador = create_agent(
    model=ChatOpenAI(model=CHAT_MODEL, temperature=0),
    tools=HERRAMIENTAS,
    system_prompt=PROMPT_ORQUESTADOR,
    name="orquestador-soporte",
)


def extraer_intent(mensajes) -> str:
    """Deduce la intencion clasificada a partir de la tool que invoco el modelo."""
    for mensaje in mensajes:
        for llamada in getattr(mensaje, "tool_calls", []) or []:
            if llamada["name"] in TOOL_A_INTENT:
                return TOOL_A_INTENT[llamada["name"]]
    return "fuera_de_alcance"


def atender_consulta(
    consulta: str,
    user_id: str = "empleado_demo",
    expected_intent: str | None = None,
    run_tag: str | None = None,
) -> dict:
    """Procesa una consulta completa y devuelve respuesta, intent y trace_id."""
    etiquetas = [t for t in (run_tag, expected_intent) if t]

    with langfuse.start_as_current_observation(
        as_type="span",
        name="support-request",
        input={"query": consulta},
    ) as raiz:
        with propagate_attributes(
            user_id=user_id,
            trace_name="support-request",
            tags=etiquetas or None,
            metadata={"expected_intent": expected_intent or "no_definido"},
        ):
            trace_id = raiz.trace_id

            with langfuse.start_as_current_observation(
                as_type="span",
                name="orchestrator-routing",
                input={"query": consulta},
            ) as span_routing:
                resultado = orquestador.invoke(
                    {"messages": [{"role": "user", "content": consulta}]},
                    config={"callbacks": [handler]},
                )
                intent = extraer_intent(resultado["messages"])
                span_routing.update(output={"intent": intent})

            respuesta = resultado["messages"][-1].content
            raiz.update(
                output={"intent": intent, "response": respuesta},
                metadata={
                    "expected_intent": expected_intent or "no_definido",
                    "actual_intent": intent,
                },
            )

    return {
        "query": consulta,
        "intent": intent,
        "response": respuesta,
        "trace_id": trace_id,
    }
