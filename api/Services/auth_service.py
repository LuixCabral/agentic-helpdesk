from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from jwt.exceptions import PyJWTError, ExpiredSignatureError

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from api.config import get_settings
from api.Models.user_model import User
from api.schemas.user_schema import TokenResponse
from api.Services.user_service import UserService


class AuthService:

    def __init__(self, db: Session) -> None:
        self.db = db
        self._user_service = UserService(db)
        self._settings = get_settings()

    def _verify_password(self, plain: str, hashed: str) -> bool:
        return bcrypt.checkpw(plain.encode(), hashed.encode())

    def _create_access_token(self, user: User) -> str:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=self._settings.jwt_expire_minutes
        )
        payload = {
            "sub": str(user.id),
            "email": user.email,
            "type": "access",
            "exp": expire,
        }
        return jwt.encode(
            payload,
            self._settings.jwt_secret,
            algorithm="HS256",
        )

    def create_refresh_token(self, user: User) -> str:
        expire = datetime.now(timezone.utc) + timedelta(
            days=self._settings.jwt_refresh_token_expire_days
        )
        payload = {
            "sub": str(user.id),
            "email": user.email,
            "type": "refresh",
            "exp": expire,
        }
        return jwt.encode(
            payload,
            self._settings.jwt_secret,
            algorithm="HS256",
        )

    def authenticate(self, email: str, password: str) -> TokenResponse:
        user = self._user_service.get_by_email(email)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciais inválidas.",
            )

        if not self._verify_password(password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciais inválidas.",
            )

        access_token = self._create_access_token(user)
        refresh_token = self.create_refresh_token(user)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    def refresh_token(self, refresh_token_str: str) -> TokenResponse:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido ou expirado.",
        )

        try:
            payload = jwt.decode(
                refresh_token_str,
                self._settings.jwt_secret,
                algorithms=["HS256"],
            )
            token_type: str = payload.get("type")
            user_id: str = payload.get("sub")

            if token_type != "refresh" or not user_id:
                raise credentials_exception

        except ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token expirado. Faça login novamente.",
            )
        except PyJWTError:
            raise credentials_exception

        user = self._user_service.get_by_id(int(user_id))

        new_access_token = self._create_access_token(user)
        new_refresh_token = self.create_refresh_token(user)

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
        )

