import json
import logging

from api.config import get_settings

from fastapi import Request
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded

logger = logging.getLogger(__name__)

# ─── Configuração via Settings centralizado ─────────────────────────────────

_settings = get_settings()
REDIS_URL: str = _settings.redis_url
CHAT_RATE_LIMIT: str = _settings.rate_limit_chat

# ─── Limiter ──────────────────────────────────────────────────────────────────

def _rate_limit_key(request: Request) -> str:
    """
    Resolve a chave de rate limiting com prioridade:
      1. user.id  — quando o usuário está autenticado (via request.state.user)
                    garante limite por usuário real, independente de IP/proxy.
      2. X-Real-IP — header injetado pelo Nginx; IP real do cliente atrás do proxy.
      3. client.host — fallback para desenvolvimento local sem proxy.
    """
    user = getattr(request.state, "user", None)
    if user is not None:
        return f"user:{user.id}"

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    return request.client.host


limiter = Limiter(
    key_func=_rate_limit_key,
    storage_uri=REDIS_URL,
    strategy="moving-window",
)

# ─── Exception handler ────────────────────────────────────────────────────────


async def rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded
) -> StreamingResponse:
    """
    Intercepta RateLimitExceeded e retorna um evento SSE de erro,
    mantendo o contrato text/event-stream do endpoint /api/chat.
    """
    rate_key = _rate_limit_key(request)
    logger.warning(
        "Rate limit excedido para %s: %s",
        rate_key,
        exc.detail,
    )

    detail = f"rate limit exceeded: {exc.detail}"

    async def sse_error():
        payload = json.dumps({"event": "error", "detail": detail})
        yield f"data: {payload}\n\n"

    return StreamingResponse(
        sse_error(),
        media_type="text/event-stream",
        status_code=429,
    )
