from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Banco de dados ────────────────────────────────────────────────────────
    database_url: str

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = ""

    # ── Rate limiting ─────────────────────────────────────────────────────────
    rate_limit_chat: str = "10/minute"

    # ── Proxy ─────────────────────────────────────────────────────────────────
    trusted_proxy_ips: str = "127.0.0.1"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",          # ignora vars desconhecidas no .env
        case_sensitive=False,
    )

    allowed_origins: list[str] = []

    api_key: str

    # ── JWT ───────────────────────────────────────────────────────────────────
    jwt_secret: str
    jwt_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
