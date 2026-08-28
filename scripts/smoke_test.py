import os
from dotenv import load_dotenv
from langfuse import get_client
from openai import OpenAI

load_dotenv()

langfuse = get_client()
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

with langfuse.start_as_current_observation(
    as_type="span",
    name="smoke-test",
    input={"query": "ping"},
) as span:
    with langfuse.start_as_current_observation(
        as_type="generation",
        name="llm-call",
        model="gpt-4o-mini",
    ) as gen:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Responde solo: pong"}],
        )
        answer = resp.choices[0].message.content
        gen.update(output=answer)
    span.update(output={"answer": answer})

langfuse.flush()
print("Respuesta:", answer)
print("Revisa el dashboard de Langfuse.")
