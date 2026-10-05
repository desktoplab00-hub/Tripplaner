import os
from strands import Agent, tool
from strands.multiagent.a2a import A2AServer

@tool
def search_flights(origin: str, destination: str, date: str) -> list[dict]:
    """Busca vuelos entre dos ciudades para una fecha (datos simulados)."""
    return [
        {"flight": "AV9821", "depart": "07:15", "price_usd": 89},
        {"flight": "LA4410", "depart": "12:40", "price_usd": 76},
        {"flight": "AV9835", "depart": "18:05", "price_usd": 102},
    ]

def create_agent(context_id: str) -> Agent:
    return Agent(
        name="Flights Agent",
        description="Busca vuelos entre ciudades para una fecha dada.",
        model="us.amazon.nova-lite-v1:0",
        system_prompt=(
        "Responde siempre en español y sin mostrar tu razonamiento. "
        "Si no te dan una fecha exacta, asume el próximo sábado (2026-09-26) "
        "y no pidas aclaraciones."
        ),
        tools=[search_flights],
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