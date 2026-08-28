"""
Agente evaluador: puntua la calidad de cada respuesta del sistema multiagente
y registra el resultado en Langfuse mediante la Score API.

El evaluador recibe la consulta original y la respuesta final, y emite un
puntaje de 1 a 10 con una justificacion breve. Usa salida estructurada para
garantizar que el puntaje sea siempre un entero en rango, sin parseo de texto.
"""

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langfuse import get_client
from pydantic import BaseModel, Field

load_dotenv()

MODELO_EVALUADOR = "gpt-4o-mini"

langfuse = get_client()


class Evaluacion(BaseModel):
    """Resultado estructurado de la evaluacion de una respuesta."""

    relevancia: int = Field(
        ge=1, le=10, description="Que tanto la respuesta atiende lo que se pregunto"
    )
    completitud: int = Field(
        ge=1, le=10, description="Si la respuesta cubre todo lo necesario"
    )
    precision: int = Field(
        ge=1,
        le=10,
        description="Si la respuesta es especifica y verificable, sin vaguedad",
    )
    puntaje: int = Field(
        ge=1, le=10, description="Puntaje global de calidad de la respuesta"
    )
    justificacion: str = Field(
        description="Explicacion breve del puntaje, maximo dos frases"
    )


PROMPT_EVALUADOR = ChatPromptTemplate.from_template(
    """Eres un evaluador de calidad de un sistema de soporte interno de empresa.

Evalua la respuesta que el sistema le dio a un empleado. Puntua de 1 a 10 en
tres dimensiones y emite un puntaje global.

- relevancia: la respuesta atiende lo que efectivamente se pregunto.
- completitud: cubre lo necesario para que el empleado pueda actuar.
- precision: es especifica y verificable (plazos, montos, canales concretos)
  en lugar de vaga o generica.

Criterios importantes:
- Una respuesta que declara honestamente no tener la informacion es preferible
  a una que inventa: penaliza poco la completitud, no la precision.
- Una respuesta correcta pero generica, sin datos concretos, no supera 6.
- Si la consulta estaba fuera del alcance del sistema, pedir aclaracion es la
  respuesta correcta y debe puntuar alto.

Consulta del empleado:
{query}

Respuesta del sistema:
{response}"""
)

evaluador = PROMPT_EVALUADOR | ChatOpenAI(
    model=MODELO_EVALUADOR, temperature=0
).with_structured_output(Evaluacion)


def evaluar(query: str, response: str) -> Evaluacion:
    """Puntua una respuesta a partir de la consulta original."""
    return evaluador.invoke({"query": query, "response": response})


def evaluar_y_registrar(query: str, response: str, trace_id: str) -> Evaluacion:
    """Evalua una respuesta y cuelga los scores de su traza en Langfuse."""
    evaluacion = evaluar(query, response)

    langfuse.create_score(
        trace_id=trace_id,
        name="calidad",
        value=float(evaluacion.puntaje),
        data_type="NUMERIC",
        comment=evaluacion.justificacion,
    )

    for dimension in ("relevancia", "completitud", "precision"):
        langfuse.create_score(
            trace_id=trace_id,
            name=dimension,
            value=float(getattr(evaluacion, dimension)),
            data_type="NUMERIC",
        )

    return evaluacion
