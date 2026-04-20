from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    display_name: str
    location_id: int | None = None


class UserCreate(BaseModel):
    username: str
    password: str
    display_name: str
    role: str
    location_id: int | None = None


class UserResponse(BaseModel):
    id: int
    username: str
    display_name: str
    role: str
    location_id: int | None
    is_active: bool

    model_config = {"from_attributes": True}
