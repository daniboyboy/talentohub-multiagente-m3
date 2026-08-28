# Sistema multiagente de soporte interno — TalentoHub

Proyecto Integrador M3. Un orquestador clasifica la intención de cada consulta mediante *function calling* y la enruta condicionalmente a uno de tres agentes RAG especializados. Todo el flujo está implementado con LangChain y trazado con Langfuse.

## Descripción

TalentoHub es una empresa SaaS de gestión de nómina y personal para LATAM. Su mesa de soporte interna recibe consultas de empleados que frecuentemente se enrutan mal: preguntas de nómina llegan a Tecnología, problemas de acceso llegan a Recursos Humanos.

Este sistema clasifica automáticamente cada consulta entrante y la delega al agente del área correspondiente, que responde fundamentado en la documentación interna de esa área.

```
Consulta del empleado
        │
        ▼
  ORQUESTADOR  (create_agent + function calling, temperature=0)
        │
        ├── consultar_recursos_humanos → Agente RAG HR       (60 chunks)
        ├── consultar_tecnologia       → Agente RAG IT       (60 chunks)
        ├── consultar_finanzas         → Agente RAG Finanzas (60 chunks)
        └── ninguna tool               → pide aclaración
        │
        ▼
   Respuesta fundamentada
```

Cada agente RAG es una cadena LCEL: `retriever → prompt → modelo → parser`.

## Estructura del repositorio

```
├── multi_agent_system.ipynb    Notebook principal, 6 secciones
├── src/
│   └── multi_agent_system.py   Implementación del sistema
├── scripts/
│   ├── build_index.py          Construye el índice vectorial de un dominio
│   ├── test_retrieval.py       Prueba la recuperación sin llamar al LLM
│   ├── run_query.py            Ejecuta una consulta suelta
│   ├── run_golden.py           Corre el golden dataset completo
│   └── smoke_test.py           Verifica conexión con OpenAI y Langfuse
├── data/
│   ├── hr_docs/                60 chunks — Recursos Humanos
│   ├── tech_docs/              60 chunks — Tecnología
│   └── finance_docs/           60 chunks — Finanzas
├── indexes/                    Índices vectoriales generados (no versionados)
├── outputs/                    Resultados de las corridas del golden dataset
├── test_queries.json           Golden dataset: 14 consultas con intent esperado
├── requirements.txt
└── .env.example
```

## Instalación

Requiere Python 3.11 o superior.

```bash
git clone <url-del-repo>
cd PIM3

python -m venv .venv
# Windows
.\.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### Configuración de credenciales

```bash
cp .env.example .env
```

Y completar el `.env` con valores reales:

| Variable | Dónde obtenerla |
|---|---|
| `OPENAI_API_KEY` | platform.openai.com → API keys |
| `LANGFUSE_PUBLIC_KEY` | cloud.langfuse.com → Settings → API Keys |
| `LANGFUSE_SECRET_KEY` | Se genera junto con la anterior; solo se muestra una vez |
| `LANGFUSE_HOST` / `LANGFUSE_BASE_URL` | La URL de tu instancia de Langfuse |

El `.env` está en `.gitignore` y nunca debe commitearse.

### Verificar la instalación

```bash
python scripts/smoke_test.py
```

Debe imprimir `Pong` y generar en Langfuse un trace `smoke-test` con un hijo anidado `llm-call`.

## Cómo ejecutar

### 1. Construir los índices (una sola vez)

```bash
python scripts/build_index.py hr
python scripts/build_index.py tech
python scripts/build_index.py finance
```

Lee los documentos de cada carpeta, los parte en chunks, verifica que haya al menos 50 por dominio, genera los embeddings y persiste el índice en `indexes/`. Aborta si algún dominio no alcanza el mínimo.

Costo aproximado: menos de un centavo de dólar en total.

### 2. Ejecutar el notebook

```bash
python -m ipykernel install --user --name pim3 --display-name "Python (PIM3)"
jupyter notebook multi_agent_system.ipynb
```

O abrirlo en VS Code y seleccionar el kernel del entorno virtual.

Las celdas se ejecutan de arriba hacia abajo. Las secciones 5 y 6 hacen llamadas reales al LLM.

### 3. Scripts de línea de comandos

Una consulta suelta:

```bash
python scripts/run_query.py "no me conecta la vpn"
```

El golden dataset completo, con etiqueta de corrida:

```bash
python scripts/run_golden.py golden-run-v1
```

Las 14 trazas quedan agrupadas bajo ese tag en Langfuse. Los resultados se guardan en `outputs/golden-run-v1.json`.

Probar solo la recuperación, sin gastar llamadas al LLM:

```bash
python scripts/test_retrieval.py hr
```

## Decisiones técnicas

### Chunking estructural por bloque Q&A

Cada chunk es una pregunta con su respuesta, delimitados por línea en blanco, y abre con una etiqueta de sección (`[Vacaciones]`, `[VPN]`) que aporta señal temática al embedding.

Se eligió sobre el chunking por ventana de caracteres por tres razones. **Integridad semántica**: un chunk nunca parte una política a la mitad. **Conteo determinista**: bloques = chunks, lo que hace verificable el mínimo de 50 por dominio sin depender de dónde caiga un contador de caracteres. **Afinidad con la consulta**: las consultas de empleados se parecen más a preguntas que a prosa de manual, así que tener la pregunta dentro del chunk mejora la similitud coseno.

Un `RecursiveCharacterTextSplitter` subdivide cualquier bloque que supere 500 tokens. Con el corpus actual no se activa (el bloque mayor tiene 55 palabras), pero deja el pipeline a prueba de documentos futuros.

### Vector store: `InMemoryVectorStore` en lugar de FAISS

`langchain-community`, donde vivía la integración de FAISS para Python, fue discontinuado en mayo de 2026 y no tiene paquete sucesor oficial. Usarlo introduciría una dependencia sin mantenimiento en el entregable.

Además, `faiss-cpu` compila código nativo: su disponibilidad depende de que exista wheel para la versión de Python y la plataforma de quien ejecute el repo. Siendo un requisito que el repositorio sea autocontenido y ejecutable, esa fragilidad es un riesgo real.

A esta escala no hay penalización de rendimiento. La ventaja de FAISS es la búsqueda aproximada, relevante por encima de decenas de miles de vectores; con 180 chunks la búsqueda exacta por coseno es instantánea.

La interfaz `Retriever` de LangChain es idéntica en ambos casos, así que cambiar de vector store sería una línea de configuración. Esa intercambiabilidad es precisamente el argumento a favor de usar un framework de orquestación.

**Nota sobre dependencias**: `numpy` aparece explícitamente en `requirements.txt` porque `InMemoryVectorStore` lo requiere para el cálculo de similitud coseno. Sin él, la persistencia funciona pero la búsqueda falla.

### `k=3` chunks recuperados

Las pruebas de recuperación aisladas mostraron brechas de similitud muy estrechas entre el primer y el segundo resultado. Ejemplo medido sobre el corpus de HR con la consulta *"cuantos dias de vacaciones tengo"*:

| Posición | Chunk | Similitud |
|---|---|---|
| 1 | Las vacaciones se cuentan en días hábiles o calendario | 0.6511 |
| 2 | **Cuántos días de vacaciones me corresponden al año** | 0.6348 |
| 3 | Puedo acumular vacaciones de un año para otro | 0.5982 |

El chunk que responde la pregunta quedó en segunda posición, a 0.016 del primero. Con `k=1` esa consulta habría fallado. Subir más allá de 3 aumentaría tokens y ruido sin beneficio observable en un corpus de bloques cortos y autocontenidos.

### Function calling en lugar de clasificación por etiqueta

El orquestador se construye con `create_agent`, que expone las tres cadenas RAG como *tools* y deja que el modelo emita una llamada a función. La alternativa habría sido pedirle una etiqueta de texto y enrutar con un `if/else`.

Se eligió function calling porque el contrato lo impone el modelo y no el parseo: no hay que validar ni normalizar una cadena que podría llegar como `"HR"`, `"Recursos Humanos"` o `"hr."`. Extender el sistema con un cuarto dominio es agregar una tool con su descripción, sin tocar lógica de enrutamiento. Y la decisión queda registrada estructuralmente como un `tool_call`, de donde se extrae el intent para la traza.

Las descripciones de las tools son el mecanismo de clasificación real: el modelo no ve el corpus, decide solo con ellas. Por eso enumeran temas concretos en vez de describir el área en abstracto, y ahí se resuelven las fronteras entre dominios.

### `temperature=0`

En el orquestador, para que la clasificación sea reproducible: la misma consulta debe enrutarse siempre igual. En los agentes, para que la respuesta se ciña al contexto recuperado en vez de elaborar sobre él.

### Instrumentación mixta de Langfuse

Los spans de orquestador y agentes se abren manualmente con `start_as_current_observation`, para controlar sus nombres y el contenido de input/output. Las generations las captura automáticamente el `CallbackHandler`.

Instrumentar todo a mano habría significado envolver cada llamada interna de LangChain; dejarlo todo al handler habría producido spans con nombres genéricos de LangGraph, difíciles de leer en el dashboard.

Jerarquía resultante:

```
support-request                    ← trace: un request completo
  └── orchestrator-routing         ← span, output: {"intent": "hr"}
       ├── generation              ← decisión del LLM
       └── hr-agent                ← span, input: query, output: respuesta
            └── generation         ← redacción de la respuesta
```

El nombre del span del agente se arma dinámicamente con el dominio, así que en la lista de trazas se ve de un vistazo a qué agente se enrutó cada consulta. `propagate_attributes` propaga `user_id`, `tags` y `expected_intent` a todos los spans; al cerrar, el span raíz registra `actual_intent`. Tener ambos valores en la misma traza convierte cada error de clasificación en un caso autoexplicativo.

### El notebook importa desde `src/` en lugar de duplicar el código

Los entregables admiten notebook único o módulos en `src/`. Duplicar la implementación en ambos crearía dos fuentes de verdad que pueden desincronizarse. El notebook aporta la documentación de decisiones y las demostraciones ejecutables; `src/` aporta la implementación, compartida con los scripts de línea de comandos.

## Resultados

Corrida `golden-run-v1` sobre las 14 consultas del golden dataset:

**Routing accuracy: 14/14 = 100%**

El dataset cubre los tres dominios con formulaciones directas y parafraseadas, más cinco casos borde:

| Tipo | Consulta | Dificultad |
|---|---|---|
| Ambiguo HR/Finanzas | "me pagaron mal la quincena" | Suena a Finanzas; la política está en HR |
| Ambiguo IT/HR | "no puedo entrar al portal de nómina" | Menciona nómina; el problema es de acceso |
| Multi-intención | "voy a renunciar, qué hago con el computador" | Toca retiro (HR) y devolución de equipo (IT) |
| Fuera de alcance | "cuál es la capital de Australia" | No debe llamar ninguna tool |
| Mal formada | "hola" | Sin intención identificable |

## Limitaciones conocidas

- **El golden dataset tiene sesgo de origen.** Corpus, descripciones de tools y consultas de prueba fueron construidos por el mismo proceso, lo que hace que compartan vocabulario. El 100% de routing accuracy mide coherencia interna del sistema, no robustez frente a consultas reales de empleados. Una validación honesta requeriría consultas recolectadas de la mesa de soporte real.
- **Sin memoria conversacional.** Cada consulta se atiende de forma independiente. Un seguimiento como "¿y cuánto se demora eso?" no tiene contexto previo.
- **Consultas multi-intención se resuelven parcialmente.** El orquestador elige un solo dominio. Una consulta que legítimamente requiere dos agentes recibe respuesta de uno.
- **El corpus es sintético.** Refleja políticas verosímiles de una empresa ficticia, no documentación real.
- **Sin evaluación automática de calidad de respuesta.** Se mide el enrutamiento, no si la respuesta generada es correcta y completa.
- **La recuperación privilegia densidad temática sobre atributo consultado.** Consultas que preguntan por un atributo específico ("cuándo", "cuánto") pueden recuperar chunks del mismo tema que no responden ese atributo. `k=3` mitiga el efecto pero no lo elimina.

## Notas de configuración

**Región de Langfuse.** Langfuse Cloud tiene instancias separadas en Europa (`cloud.langfuse.com`) y Estados Unidos (`us.cloud.langfuse.com`). Las llaves de un proyecto solo funcionan contra la instancia donde ese proyecto vive. Si al ejecutar aparece `401 Unauthorized` con el mensaje sobre confirmar el host, verificar la URL del dashboard en el navegador y ajustar `LANGFUSE_HOST` y `LANGFUSE_BASE_URL` en consecuencia.

**Dos variables para el host.** El `.env.example` incluye `LANGFUSE_HOST` y `LANGFUSE_BASE_URL` con el mismo valor. El SDK v4 de Langfuse lee `LANGFUSE_BASE_URL`; `LANGFUSE_HOST` se mantiene por compatibilidad con la convención de la documentación.

**Los índices no se versionan.** `indexes/` está en `.gitignore` porque son artefactos regenerables desde `data/`. Hay que ejecutar `build_index.py` para los tres dominios antes de correr el notebook.

**Costo estimado.** Construir los tres índices cuesta menos de un centavo. Cada consulta al sistema hace dos llamadas a `gpt-4o-mini` (clasificación y generación). Una corrida completa del golden dataset cuesta unos pocos centavos.

## Stack

| Componente | Elección |
|---|---|
| Orquestación | LangChain 1.x (`create_agent`, LCEL) |
| Modelo de chat | `gpt-4o-mini`, temperature=0 |
| Embeddings | `text-embedding-3-small` |
| Vector store | `InMemoryVectorStore` (langchain-core) |
| Observabilidad | Langfuse SDK v4 |
