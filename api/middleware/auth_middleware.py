import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from api.config import get_settings
from api.dependencies import _get_session_factory
from api.Services.user_service import UserService

logger = logging.getLogger(__name__)


class AuthStateMiddleware(BaseHTTPMiddleware):
    """
    Popula request.state.user a partir do token Bearer JWT antes
    que o SlowAPIMiddleware avalie o key_func do rate limiter.

    O SlowAPI resolve o key_func ANTES dos Depends() do endpoint,
    então o usuário autenticado precisa estar em request.state para
    que o rate limit seja aplicado por user.id e não por IP.

    Fluxo de fallback em _rate_limit_key (rate_limit.py):
      1. request.state.user.id  → usuário autenticado
      2. X-Real-IP              → IP real via Nginx
      3. request.client.host    → desenvolvimento local
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        request.state.user = None

        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.removeprefix("Bearer ")
            db = None
            try:
                settings = get_settings()
                db = _get_session_factory()()
                service = UserService(db)
                request.state.user = service.get_authenticated_user(
                    token, settings.jwt_secret
                )
            except Exception:
                # Token inválido ou expirado: rate limit cai para X-Real-IP
                pass
            finally:
                if db is not None:
                    db.close()

        return await call_next(request)
