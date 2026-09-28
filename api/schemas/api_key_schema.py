from pydantic import BaseModel


class ApiKeyResponse(BaseModel):
    id: int
    key: str
    is_active: bool

    model_config = {"from_attributes": True}
