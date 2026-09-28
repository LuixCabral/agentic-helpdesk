from pydantic import BaseModel, EmailStr, Field


class UserCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255, description="Nome do usuário")
    email: EmailStr = Field(..., description="E-mail do usuário")
    password: str = Field(..., min_length=8, description="Senha do usuário")


class UserUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    email: EmailStr | None = Field(default=None)
    password: str | None = Field(default=None, min_length=8)


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    is_deleted: bool

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str