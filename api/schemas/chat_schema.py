from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):

    message: str = Field(..., description="Mensagem do usuário N1 em linguagem natural.")
    session_id: str | None = Field(
        default=None,
        description=(
            "UUID de sessão gerado pelo cliente. "
            "Isola o histórico de conversa no PostgreSQL por session_id."
        ),
    )


class StreamEvent(BaseModel):
    event: Literal["session", "delta", "done", "error"]
    session_id: str | None = None
    content: str | None = None
    agent_name: str | None = None
    detail: str | None = None
