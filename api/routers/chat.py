import json
import uuid
import logging

from agno.run.agent import RunStartedEvent as AgentRunStartedEvent
from agno.run.team import RunContentEvent as TeamRunContentEvent

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from agno.team import Team

from api.dependencies import get_agent, validate_api_key
from api.rate_limit import limiter, CHAT_RATE_LIMIT
from api.schemas.chat import ChatRequest

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


def _sse(**kwargs) -> str:
    """Serializa um dict como linha SSE."""
    return f"data: {json.dumps(kwargs)}\n\n"


@router.post(
    "/chat",
    summary="Enviar mensagem ao agente",
    description=(
        "Recebe a mensagem do usuário N1 e o session_id, "
        "executa o agente (com histórico isolado por sessão no PostgreSQL) "
        "e retorna a resposta em streaming SSE (text/event-stream)."
    ),
)
@limiter.limit(CHAT_RATE_LIMIT)
async def chat(
    request: Request,
    body: ChatRequest,
    agent: Team = Depends(get_agent),
    _: str = Depends(validate_api_key),
) -> StreamingResponse:
    session_id = body.session_id or str(uuid.uuid4())

    async def event_generator():
        try:
            yield _sse(event="session", session_id=session_id)

            active_agent: str = "assistant"  # membro acionado pelo TriageAgent

            async for chunk in agent.arun(
                body.message,
                session_id=session_id,
                stream=True,
                stream_events=True,
            ):
                if isinstance(chunk, AgentRunStartedEvent):
                    # Registra qual agente membro foi acionado
                    active_agent = chunk.agent_name or "assistant"
                elif isinstance(chunk, TeamRunContentEvent) and chunk.content:
                    # Síntese final do TriageAgent — identifica com o membro que respondeu
                    yield _sse(
                        event="delta",
                        content=chunk.content,
                        agent_name=active_agent,
                    )

            yield _sse(event="done")

        except Exception as exc:
            logger.error("Erro no stream do agente: %s", exc)
            yield _sse(event="error", detail=str(exc))

    return StreamingResponse(event_generator(), media_type="text/event-stream")
