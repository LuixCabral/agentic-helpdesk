from collections.abc import Generator
from functools import lru_cache

from fastapi import Depends, Request, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from agno.team import Team

from api.config import get_settings, Settings
from api.Models.user_model import User
from api.Services.user_service import UserService


def get_agent(request: Request) -> Team:
    return request.app.state.team


def get_settings_dep() -> Settings:
    return get_settings()


def to_sync_database_url(database_url: str) -> str:
    """Converte a DATABASE_URL para o driver síncrono psycopg (v3)."""
    return (
        database_url
        .replace("+psycopg_async", "+psycopg")
        .replace("+asyncpg", "+psycopg")
    )


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Engine único por processo — compartilha o pool de conexões."""
    settings = get_settings()
    return create_engine(
        to_sync_database_url(settings.database_url),
        pool_pre_ping=True,
    )


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker:
    return sessionmaker(bind=get_engine(), autocommit=False, autoflush=False)


def get_db() -> Generator[Session, None, None]:
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def validate_api_key(
    api_key: str | None = Security(api_key_header),
    settings: Settings = Depends(get_settings_dep),
):
    if not api_key or api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return api_key


security_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(security_bearer),
    settings: Settings = Depends(get_settings_dep),
    db: Session = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticação não fornecido.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_service = UserService(db)
    authenticated_user  = user_service.get_authenticated_user(credentials.credentials , settings.jwt_secret)
    return authenticated_user