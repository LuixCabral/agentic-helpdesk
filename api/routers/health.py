import asyncio
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from api.config import Settings
from api.dependencies import get_settings_dep
from api.Services import DatabaseService, CacheService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


# ── Liveness ──────────────────────────────────────────────────────────────────

@router.get(
    "/live",
    summary="Liveness probe",
    description="Retorna 200 sempre. Indica que o processo está vivo.",
)
async def liveness() -> JSONResponse:
    return JSONResponse(status_code=200, content={"status": "ok"})


# ── Readiness ─────────────────────────────────────────────────────────────────

@router.get(
    "/ready",
    summary="Readiness probe",
    description=(
        "Verifica Postgres e Redis. "
        "Retorna 200 quando tudo está acessível, 503 se alguma dependência falhar."
    ),
)
async def readiness(
    settings: Settings = Depends(get_settings_dep),
) -> JSONResponse:
    # Normaliza o DSN para psycopg puro (sem prefixo de driver SQLAlchemy)
    pg_dsn = (
        settings.database_url
        .replace("postgresql+psycopg_async://", "postgresql://")
        .replace("postgresql+asyncpg://", "postgresql://")
        .replace("postgresql+psycopg://", "postgresql://")
    )

    checks: dict[str, str] = {}

    # Executa os checks em paralelo para minimizar latência total
    db_ok, cache_ok = await asyncio.gather(
        DatabaseService(pg_dsn).check_db_health(),
        CacheService(settings.redis_url).check_cache_health()
        if settings.redis_url
        else asyncio.coroutine(lambda: True)(),
    )

    checks["postgres"] = "ok" if db_ok else "unreachable"

    if settings.redis_url:
        checks["redis"] = "ok" if cache_ok else "unreachable"
    else:
        checks["redis"] = "not_configured"
        logger.warning("Readiness – REDIS_URL não configurada; pulando verificação.")

    has_errors = any(v == "unreachable" for v in checks.values())

    if has_errors:
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "checks": checks},
        )

    return JSONResponse(status_code=200, content={"status": "ok", "checks": checks})
