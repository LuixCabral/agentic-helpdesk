from api.schemas.user_schema import RefreshTokenRequest
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.dependencies import get_db
from api.schemas.user_schema import UserCreateRequest, UserResponse, TokenResponse
from api.Services.user_service import UserService
from api.Services.auth_service import AuthService

router = APIRouter(tags=["users"])


@router.post("/create_user", response_model=UserResponse, status_code=201)
def create_user(
    request: UserCreateRequest,
    db: Session = Depends(get_db),
) -> UserResponse:

    user_service = UserService(db)
    user = user_service.create(request)

    return user


@router.query("/login", response_model=TokenResponse, status_code=200)
def login(
    request: UserCreateRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:

    auth_service = AuthService(db)
    return auth_service.authenticate(request.email, request.password)


@router.post("/refresh", response_model=TokenResponse, status_code=200)
def refresh_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:

    auth_service = AuthService(db)
    return auth_service.refresh_token(request.refresh_token)
