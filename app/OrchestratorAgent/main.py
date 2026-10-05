import os

import boto3
import httpx
from a2a.client import A2ACardResolver, ClientConfig, ClientFactory
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent, tool
from strands.agent.a2a_agent import A2AAgent

app = BedrockAgentCoreApp()

REGION = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-2"

# Endpoints de los especialistas (inyectados por variables de entorno)
FLIGHTS_URL = os.environ["FLIGHTS_AGENT_URL"]
WEATHER_URL = os.environ["WEATHER_AGENT_URL"]


class SigV4HttpxAuth(httpx.Auth):
    """Firma cada petición saliente con SigV4 (servicio bedrock-agentcore)."""

    requires_request_body = True

    def auth_flow(self, request):
        credentials = boto3.Session().get_credentials().get_frozen_credentials()
        headers = {}
        if "content-type" in request.headers:
            headers["Content-Type"] = request.headers["content-type"]
        aws_request = AWSRequest(
            method=request.method,
            url=str(request.url),
            data=request.content,
            headers=headers,
        )
        SigV4Auth(credentials, "bedrock-agentcore", REGION).add_auth(aws_request)
        for name in ("Authorization", "X-Amz-Date", "X-Amz-Security-Token"):
            if name in aws_request.headers:
                request.headers[name] = aws_request.headers[name]
        yield request


class SignedA2AAgent(A2AAgent):
    """A2AAgent que también firma con SigV4 la petición de la agent card."""

    def __init__(self, endpoint: str, **kwargs):
        super().__init__(endpoint=endpoint, **kwargs)
        self._signed_endpoint = endpoint

    async def get_agent_card(self):
        if getattr(self, "_agent_card", None) is None:
            async with httpx.AsyncClient(auth=SigV4HttpxAuth(), timeout=60) as client:
                resolver = A2ACardResolver(httpx_client=client, base_url=self._signed_endpoint)
                self._agent_card = await resolver.get_agent_card()
        return self._agent_card


def make_remote(endpoint: str) -> A2AAgent:
    http_client = httpx.AsyncClient(auth=SigV4HttpxAuth(), timeout=120)
    factory = ClientFactory(ClientConfig(httpx_client=http_client))
    return SignedA2AAgent(endpoint=endpoint, a2a_client_factory=factory)


@tool
def ask_flights(request: str) -> str:
    """Delega en el Flights Agent la búsqueda de vuelos."""
    remote = make_remote(FLIGHTS_URL)
    return str(remote(request).message)


@tool
def ask_weather(request: str) -> str:
    """Delega en el Weather Agent la consulta de clima."""
    remote = make_remote(WEATHER_URL)
    return str(remote(request).message)


SYSTEM_PROMPT = (
    "Eres un planificador de viajes. Usa ask_flights para vuelos y "
    "ask_weather para clima. Consolida ambos resultados en una respuesta clara. "
    "Responde en español. Si el usuario no da una fecha exacta, "
    "asume el próximo sábado (2026-09-26) y no preguntes."
)


def build_agent() -> Agent:
    return Agent(
        name="Trip Planner Orchestrator",
        system_prompt=SYSTEM_PROMPT,
        model="us.amazon.nova-lite-v1:0",
        tools=[ask_flights, ask_weather],
        callback_handler=None,
    )


@app.entrypoint
async def invoke(payload, context):
    prompt = payload.get("prompt", "")
    if not isinstance(prompt, str):
        raise ValueError("prompt debe ser un string")
    agent = build_agent()
    async for event in agent.stream_async(prompt):
        yield event


if __name__ == "__main__":
    app.run()