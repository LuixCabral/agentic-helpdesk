import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from agno.db.postgres import PostgresDb
from agno.tools.mcp import MCPTools
from mcp import StdioServerParameters

from Ai import build_team
from api.config import get_settings
from api.middleware.auth_middleware import AuthStateMiddleware
from api.rate_limit import limiter, rate_limit_exceeded_handler
from api.routers import chat_router, health_router, user_router

load_dotenv()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    database_url = settings.database_url

    sync_url = database_url.replace("+psycopg_async", "+psycopg").replace(
        "+asyncpg", "+psycopg"
    )
    db = PostgresDb(db_url=sync_url)

    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "jira_mcp.server"],
        env={**os.environ},
    )
    notion_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "notion_mcp.server"],
        env={**os.environ},
    )

    logger.info("Iniciando MCPTools (jira_mcp.server)...")
    async with MCPTools(
        server_params=server_params,
        exclude_tools=["get_project_info"],
        timeout_seconds=30,
    ) as jira_tools:
        logger.info("Iniciando MCPTools (notion_mcp.server)...")
        async with MCPTools(server_params=notion_params, timeout_seconds=60) as notion_tools:
            logger.info("MCPTools inicializados. Construindo team...")
            app.state.team = build_team(jira_tools, notion_tools, db=db)
            logger.info("Team pronto. API disponível.")
            yield

    logger.info("MCPTools encerrados. Shutdown concluído.")


app = FastAPI(
    title="Bug Reporter Agent API",
    description=(
        "API HTTP para o agente N1 de abertura automática de chamados Jira. "
        "O histórico de cada sessão é persistido no PostgreSQL."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# ─── Trusted proxies (anti X-Forwarded-For spoofing) ────────────────────────
_trusted_proxies = get_settings().trusted_proxy_ips
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=_trusted_proxies)

# ─── Rate limiting ────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
# AuthStateMiddleware deve vir ANTES do SlowAPIMiddleware para que
# request.state.user esteja disponível quando o key_func for avaliado.
app.add_middleware(AuthStateMiddleware)
app.add_middleware(SlowAPIMiddleware)

# ─── Middleware ───────────────────────────────────────────────────────────────
app.add_middleware(CORSMiddleware, allow_origins=get_settings().allowed_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# ─── Routers ─────────────────────────────────────────────────────────────────
app.include_router(chat_router.router, prefix="/api")
app.include_router(health_router.router, prefix="/health")
app.include_router(user_router.router, prefix="/api")
