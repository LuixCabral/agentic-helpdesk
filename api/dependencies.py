from fastapi import Request
from agno.team import Team

from api.config import get_settings, Settings


def get_agent(request: Request) -> Team:
    return request.app.state.team


def get_settings_dep() -> Settings:
    return get_settings()
