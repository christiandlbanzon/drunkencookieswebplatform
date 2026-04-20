from pydantic import BaseModel
from datetime import date


class InventoryRow(BaseModel):
    flavor_id: int
    flavor_code: str
    flavor_name: str
    beginning_inventory: int
    sent_cookies: int
    received_cookies: int
    opening_stock: int
    live_sales: int
    second_delivery: int
    closing_inventory: int
    # Waste tracking
    expired: int = 0
    flawed: int = 0
    used_as_display: int = 0
    given_away: int = 0
    production_waste: int = 0

    model_config = {"from_attributes": True}


class InventoryResponse(BaseModel):
    inventory_date: date
    location_id: int
    location_name: str
    rows: list[InventoryRow]


class InventoryUpdate(BaseModel):
    beginning_inventory: int | None = None
    sent_cookies: int | None = None
    received_cookies: int | None = None
    second_delivery: int | None = None
    closing_inventory: int | None = None
    expired: int | None = None
    flawed: int | None = None
    used_as_display: int | None = None
    given_away: int | None = None
    production_waste: int | None = None
