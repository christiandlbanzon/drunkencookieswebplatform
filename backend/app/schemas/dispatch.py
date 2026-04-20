from pydantic import BaseModel
from datetime import date


class DispatchRow(BaseModel):
    flavor_id: int
    flavor_code: str
    flavor_name: str
    sales_trend_median: float
    par_value: float
    adjusted_par: int
    live_inventory: int
    amount_to_send: int
    override_amount: int | None = None
    dispatch_status: str = "pending"

    model_config = {"from_attributes": True}


class DispatchLocationBlock(BaseModel):
    location_id: int
    location_name: str
    rows: list[DispatchRow]
    total_to_send: int
    dispatch_status: str = "pending"


class DispatchPlanResponse(BaseModel):
    plan_date: date
    locations: list[DispatchLocationBlock]
    sync_warning: str | None = None


class DispatchOverride(BaseModel):
    override_amount: int | None = None
