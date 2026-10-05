import os
from strands import Agent, tool
from strands.multiagent.a2a import A2AServer

@tool
def get_forecast(city: str, date: str) -> dict:
    """Devuelve el pronóstico del clima de una ciudad (datos simulados)."""
    return {"city": city, "date": date, "temp_c": 31, "condition": "Soleado"}

def create_agent(context_id: str) -> Agent:
    return Agent(
        name="Weather Agent",
        description="Consulta el pronóstico del clima por ciudad y fecha.",
        model="us.amazon.nova-lite-v1:0",
        system_prompt=(
        "Responde siempre en español y sin mostrar tu razonamiento. "
        "Si no te dan una fecha exacta, asume el próximo sábado (2026-09-26) "
        "y no pidas aclaraciones."
        ),
        tools=[get_forecast],
        callback_handler=None,
    )

runtime_url = os.environ.get("AGENTCORE_RUNTIME_URL", "http://127.0.0.1:9000/")

a2a_server = A2AServer(
    agent_factory=create_agent,
    host="0.0.0.0",
    port=9000,
    http_url=runtime_url,
    serve_at_root=True,
)

if __name__ == "__main__":
    a2a_server.serve()