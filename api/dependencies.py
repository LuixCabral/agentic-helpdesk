from fastapi import Depends, Request, HTTPException, Security
from fastapi.security import APIKeyHeader

from agno.team import Team

from api.config import get_settings, Settings


def get_agent(request: Request) -> Team:
    return request.app.state.team


def get_settings_dep() -> Settings:
    return get_settings()

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def validate_api_key(
    api_key: str | None = Security(api_key_header),
    settings: Settings = Depends(get_settings_dep),
):
    if not api_key or api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return api_key