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

limiter = Limiter(
    key_func=lambda request: request.client.host,
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
    logger.warning(
        "Rate limit excedido para o IP %s: %s",
        request.client.host,
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
