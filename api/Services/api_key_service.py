import secrets

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from api.Models.api_key_model import ApiKey
from api.Models.user_model import User


class ApiKeyService:

    def __init__(self, db: Session) -> None:
        self.db = db

    def _generate_key(self) -> str:
        return f"ak_{secrets.token_urlsafe(32)}"

    def create_api_key(self, user_id: int) -> ApiKey:
        user = self.db.query(User).filter(User.id == user_id, User.is_deleted == False).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado.",
            )

        key = ApiKey.create_api_key(
            key=self._generate_key(),
            user_id=user_id,
        )
        self.db.add(key)
        self.db.commit()
        self.db.refresh(key)
        return key

    def list_active(self, user_id: int) -> list[ApiKey]:
        return (
            self.db.query(ApiKey)
            .filter(ApiKey.user_id == user_id, ApiKey.is_active == True)
            .all()
        )

    def revoke(self, key_id: int, user_id: int) -> ApiKey:
        key = (
            self.db.query(ApiKey)
            .filter(ApiKey.id == key_id, ApiKey.user_id == user_id)
            .first()
        )
        if not key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key não encontrada.",
            )
        if not key.is_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="API key já está revogada.",
            )

        key.is_active = False
        self.db.commit()
        self.db.refresh(key)
        return key

    def validate(self, raw_key: str) -> ApiKey:
        key = (
            self.db.query(ApiKey)
            .filter(ApiKey.key == raw_key, ApiKey.is_active == True)
            .first()
        )
        if not key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key inválida ou revogada.",
            )
        return key