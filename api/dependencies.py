from collections.abc import Generator

from fastapi import Depends, Request, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from agno.team import Team

from api.config import get_settings, Settings
from api.Models.user_model import User
from api.Services.user_service import UserService


def get_agent(request: Request) -> Team:
    return request.app.state.team


def get_settings_dep() -> Settings:
    return get_settings()


def _get_session_factory() -> sessionmaker:
    settings = get_settings()
    sync_url = (
        settings.database_url
        .replace("+psycopg_async", "+psycopg")
        .replace("+asyncpg", "+psycopg")
    )
    engine = create_engine(sync_url)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


_SessionFactory: sessionmaker | None = None


def get_db() -> Generator[Session, None, None]:
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = _get_session_factory()
    db = _SessionFactory()
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