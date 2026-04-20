from pydantic import BaseModel
from datetime import date


class LocationResponse(BaseModel):
    id: int
    name: str
    display_name: str
    sort_order: int
    is_active: bool

    model_config = {"from_attributes": True}


class FlavorResponse(BaseModel):
    id: int
    code: str
    name: str
    sort_order: int
    is_core: bool
    is_active: bool
    category: str = "cookie"

    model_config = {"from_attributes": True}


class FlavorUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None
    is_core: bool | None = None


class FlavorCreate(BaseModel):
    code: str
    name: str
    sort_order: int
    is_core: bool = True
    is_active: bool = True
    category: str = "cookie"


class UserResponse(BaseModel):
    id: int
    username: str
    display_name: str
    role: str
    location_id: int | None
    is_active: bool

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    username: str
    password: str
    display_name: str
    role: str
    location_id: int | None = None


class UserUpdate(BaseModel):
    display_name: str | None = None
    role: str | None = None
    location_id: int | None = None
    is_active: bool | None = None
    password: str | None = None


class ParSettingsResponse(BaseModel):
    location_id: int
    effective_date: date
    reduction_pct: float
    minimum_par: int
    median_weeks: int

    model_config = {"from_attributes": True}


class ParSettingsUpdate(BaseModel):
    reduction_pct: float | None = None
    minimum_par: int | None = None
    median_weeks: int | None = None
