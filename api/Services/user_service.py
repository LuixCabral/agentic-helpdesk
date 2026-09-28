import bcrypt

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from api.Models.user_model import User
from api.schemas.user_schema import UserCreateRequest, UserUpdateRequest


class UserService:

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, data: UserCreateRequest) -> User:
        existing = self.db.query(User).filter(User.email == data.email).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="E-mail já cadastrado.",
            )

        hashed_password = bcrypt.hashpw(data.password.encode(), bcrypt.gensalt()).decode()

        user = User.create_user(
            name=data.name,
            email=data.email,
            password=hashed_password,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_by_id(self, user_id: int) -> User:
        user = (
            self.db.query(User)
            .filter(User.id == user_id, User.is_deleted == False)
            .first()
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado.",
            )
        return user

    def get_by_email(self, email: str) -> User | None:
        return (
            self.db.query(User)
            .filter(User.email == email, User.is_deleted == False)
            .first()
        )


    def update(self, user_id: int, data: UserUpdateRequest) -> User:
        user = self.get_by_id(user_id)

        new_hashed_password = (
            bcrypt.hashpw(data.password.encode(), bcrypt.gensalt()).decode()
            if data.password
            else user.password
        )
        user.update_user(
            name=data.name or user.name,
            email=data.email or user.email,
            password=new_hashed_password,
        )
        self.db.commit()
        self.db.refresh(user)
        return user

    def soft_delete(self, user_id: int) -> User:
        user = self.get_by_id(user_id)
        user.soft_delete_user()
        self.db.commit()
        self.db.refresh(user)
        return user
