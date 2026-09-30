from api.schemas.api_key_schema import ApiKeyResponse
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.dependencies import get_current_user, get_db
from api.Services.api_key_service import ApiKeyService

router = APIRouter(tags=["api_keys"])

@router.post("/generate_api_key", status_code=201)
def generate_api_key(
    user = Depends(get_current_user),
    db: Session = Depends(get_db),
)->ApiKeyResponse:

    api_key_service = ApiKeyService(db)
    new_api_key = api_key_service.create_api_key(user.id)
    return ApiKeyResponse(api_key=new_api_key)

    
